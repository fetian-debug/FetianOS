"""Unprivileged Linux file operations with descriptor-relative traversal.

No privileged helpers, no implicit overwrite, and no shell execution. Copy jobs
commit a private staging tree only on success. renameat2(NOREPLACE) is required;
we fail rather than downgrade to a clobber-prone rename on unsupported systems.
"""
from contextlib import contextmanager
import ctypes
import errno
import os
from pathlib import Path
import stat
import re
import threading
import uuid


class Cancelled(Exception):
    pass


class Token:
    def __init__(self): self.event = threading.Event()
    def cancel(self): self.event.set()
    def check(self):
        if self.event.is_set(): raise Cancelled("Operation cancelled; completed changes may remain")


def name(value):
    if not isinstance(value, str) or value in ("", ".", "..") or "/" in value or "\0" in value:
        raise ValueError("A single nonempty filename is required")
    return value


@contextmanager
def directory(path):
    if os.name != "posix": raise OSError("FetianFiles file operations require Linux")
    path = Path(path).expanduser().absolute()
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            name(part)
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


def rename_no_replace(source_fd, source, target_fd, target):
    name(source); name(target)
    libc = ctypes.CDLL(None, use_errno=True)
    operation = getattr(libc, "renameat2", None)
    if operation is None: raise OSError(errno.ENOTSUP, "Atomic no-overwrite rename is unavailable")
    operation.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    operation.restype = ctypes.c_int
    if operation(source_fd, os.fsencode(source), target_fd, os.fsencode(target), 1):
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), target)


def _remove(parent, child, token, private=False):
    token.check()
    info = os.stat(child, dir_fd=parent, follow_symlinks=False)
    if stat.S_ISDIR(info.st_mode):
        fd = os.open(child, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        try:
            if private: os.fchmod(fd, info.st_mode | 0o700)
            for entry in os.listdir(fd): _remove(fd, entry, token, private)
        finally: os.close(fd)
        os.rmdir(child, dir_fd=parent)
    else:
        os.unlink(child, dir_fd=parent)


@contextmanager
def transaction(destination):
    with directory(destination) as parent:
        temporary = ".fetian-job-" + uuid.uuid4().hex
        os.mkdir(temporary, 0o700, dir_fd=parent)
        fd = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        try:
            yield parent, fd, temporary
        finally:
            os.close(fd)
            _remove(parent, temporary, Token(), private=True)


def _copy(source_parent, source, destination_parent, destination, token, progress):
    token.check()
    before = os.stat(source, dir_fd=source_parent, follow_symlinks=False)
    if stat.S_ISLNK(before.st_mode):
        os.symlink(os.readlink(source, dir_fd=source_parent), destination, dir_fd=destination_parent)
    elif stat.S_ISDIR(before.st_mode):
        source_fd = os.open(source, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=source_parent)
        target_fd = None
        try:
            opened = os.fstat(source_fd)
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                raise OSError("Source directory changed while opening")
            os.mkdir(destination, 0o700, dir_fd=destination_parent)
            target_fd = os.open(destination, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=destination_parent)
            for child in os.listdir(source_fd): _copy(source_fd, child, target_fd, child, token, progress)
            # Owner access is retained for transaction cleanup and usable copies.
            os.fchmod(target_fd, (before.st_mode & 0o077) | 0o700)
        finally:
            os.close(source_fd)
            if target_fd is not None: os.close(target_fd)
    elif stat.S_ISREG(before.st_mode):
        source_fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=source_parent)
        target_fd = None
        try:
            opened = os.fstat(source_fd)
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                raise OSError("Source changed while opening")
            target_fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=destination_parent)
            while True:
                token.check()
                block = os.read(source_fd, 128 * 1024)
                if not block: break
                view = memoryview(block)
                while view:
                    written = os.write(target_fd, view)
                    if written <= 0: raise OSError("Unable to write destination")
                    view = view[written:]
                progress(len(block))
            after = os.fstat(source_fd)
            if (opened.st_size, opened.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise OSError("Source changed during copy; output was not committed")
            os.fchmod(target_fd, before.st_mode & 0o777)
            os.utime(target_fd, ns=(before.st_atime_ns, before.st_mtime_ns))
            os.fsync(target_fd)
        finally:
            os.close(source_fd)
            if target_fd is not None: os.close(target_fd)
    else:
        raise ValueError("Devices, sockets and pipes cannot be copied")


def copy(source, destination, token=None, progress=lambda count: None):
    token = token or Token()
    source, destination = Path(source).absolute(), Path(destination).absolute()
    if source.is_dir() and not source.is_symlink() and destination.is_relative_to(source):
        raise ValueError("Cannot copy a folder into itself")
    name(destination.name)
    with directory(source.parent) as parent, transaction(destination.parent) as (target, temporary, _):
        _copy(parent, source.name, temporary, "payload", token, progress)
        token.check()
        rename_no_replace(temporary, "payload", target, destination.name)
    return str(destination)


def move(source, destination, token=None):
    token = token or Token(); token.check()
    source, destination = Path(source).absolute(), Path(destination).absolute()
    with directory(source.parent) as parent, directory(destination.parent) as target:
        before = os.stat(source.name, dir_fd=parent, follow_symlinks=False)
        try:
            rename_no_replace(parent, source.name, target, destination.name)
        except OSError as error:
            if error.errno != errno.EXDEV: raise
            if not stat.S_ISREG(before.st_mode):
                raise OSError("Cross-device folder/link move is not supported; copy first and verify it before trashing the source") from error
            copy(source, destination, token)
            current = os.stat(source.name, dir_fd=parent, follow_symlinks=False)
            if (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
                raise OSError("Copy completed, but the source changed and was retained")
            os.unlink(source.name, dir_fd=parent)
    info = destination.lstat()
    return {"source": str(source), "destination": str(destination), "identity": (info.st_dev, info.st_ino)}


def undo_move(receipt):
    destination = Path(receipt["destination"])
    info = destination.lstat()
    if (info.st_dev, info.st_ino) != tuple(receipt["identity"]):
        raise ValueError("Undo target was replaced; refusing to modify it")
    return move(destination, receipt["source"])


def create(path, folder=False):
    path = Path(path).absolute(); name(path.name)
    with directory(path.parent) as parent:
        if folder: os.mkdir(path.name, 0o755, dir_fd=parent)
        else:
            fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
            os.close(fd)


def permissions(path, mode):
    if type(mode) is not int or not 0 <= mode <= 0o777: raise ValueError("Use ordinary permission bits, 000–777")
    path = Path(path).absolute()
    with directory(path.parent) as parent:
        before = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        if not (stat.S_ISREG(before.st_mode) or stat.S_ISDIR(before.st_mode)):
            raise ValueError("Permissions can only be edited on a local regular file or directory")
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            opened = os.fstat(fd)
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino): raise OSError("Permission target changed")
            os.fchmod(fd, mode)
        finally: os.close(fd)


def batch_rename(sources, pattern, token=None):
    """No swaps or overwrite; rollback completed renames where identity permits."""
    token = token or Token(); sources = [Path(path).absolute() for path in sources]
    if not sources or len(sources) > 1000: raise ValueError("Select 1–1,000 items")
    if len(set(sources)) != len(sources) or len({path.parent for path in sources}) != 1:
        raise ValueError("Batch rename requires unique items in the same directory")
    if len(pattern) > 255 or "{" in re.sub(r"\{(?:name|stem|suffix|n)\}", "", pattern) or "}" in re.sub(r"\{(?:name|stem|suffix|n)\}", "", pattern):
        raise ValueError("Only {name}, {stem}, {suffix}, and {n} placeholders are supported")
    targets = [path.with_name(name(pattern.format(name=path.name, stem=path.stem, suffix=path.suffix, n=index))) for index, path in enumerate(sources, 1)]
    if len(set(targets)) != len(targets): raise ValueError("Pattern produces duplicate names")
    with directory(sources[0].parent) as parent:
        for source, target in zip(sources, targets):
            if len(os.fsencode(target.name)) > 255: raise ValueError("Generated filename exceeds 255 bytes")
            if source == target: continue
            try: os.stat(target.name, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError: pass
            else: raise FileExistsError("Batch destination exists: " + target.name)
    receipts = []
    try:
        for source, target in zip(sources, targets):
            token.check()
            if source != target: receipts.append(move(source, target, token))
    except Exception as error:
        failed = []
        for receipt in reversed(receipts):
            try: undo_move(receipt)
            except OSError: failed.append(receipt["destination"])
            except ValueError: failed.append(receipt["destination"])
        raise RuntimeError(f"Batch rename stopped: {error}. Rollback incomplete for {len(failed)} item(s): {failed}") from error
    return receipts


def delete(path, *, confirmed=False, token=None):
    if not confirmed: raise ValueError("Permanent deletion requires explicit confirmation")
    path = Path(path).absolute(); name(path.name)
    with directory(path.parent) as parent: _remove(parent, path.name, token or Token())


def preview_text(path, limit=128 * 1024):
    path = Path(path).absolute()
    with directory(path.parent) as parent:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode): raise ValueError("Only regular files can be previewed")
            data = os.read(fd, limit + 1)
        finally: os.close(fd)
    if b"\0" in data: raise ValueError("Binary preview is unavailable")
    return data[:limit].decode("utf-8", errors="replace"), len(data) > limit


def search(root, query, token=None, limit=2000, examined_limit=50000, minimum=0, maximum=None, kind="any", modified_after=None):
    if kind not in ("any", "file", "folder") or minimum < 0 or (maximum is not None and maximum < minimum):
        raise ValueError("Invalid search filters")
    token = token or Token(); results = []; examined = 0; stack = [Path(root).absolute()]
    while stack:
        token.check()
        current = stack.pop()
        try:
            with directory(current) as fd:
                for child in os.listdir(fd):
                    token.check(); examined += 1
                    if examined > examined_limit: return results, True
                    info = os.stat(child, dir_fd=fd, follow_symlinks=False)
                    path = current / child
                    matches_kind = kind == "any" or (kind == "file" and stat.S_ISREG(info.st_mode)) or (kind == "folder" and stat.S_ISDIR(info.st_mode))
                    if matches_kind and (modified_after is None or info.st_mtime >= modified_after) and query.casefold() in child.casefold() and info.st_size >= minimum and (maximum is None or info.st_size <= maximum):
                        results.append(str(path))
                        if len(results) >= limit: return results, True
                    if stat.S_ISDIR(info.st_mode): stack.append(path)
        except PermissionError:
            continue
    return results, False
