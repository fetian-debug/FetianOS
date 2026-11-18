"""ZIP/TAR extraction without extractall, links, overwrites or unbounded output.

The CLI is the resource-limited archive worker used by the GUI. This is not a
filesystem/network sandbox; archive formats never execute their contents.
"""
from contextlib import contextmanager
import argparse
import gzip
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tarfile
import zipfile

from fileops import Token, directory, name, transaction, rename_no_replace

MAX_ENTRIES = 10000
MAX_FILE = 256 * 1024 * 1024
MAX_TOTAL = 1024 * 1024 * 1024
MAX_INPUT = 256 * 1024 * 1024


def parts(value):
    if "\0" in value or "\\" in value or value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise ValueError("Unsafe archive path")
    path = PurePosixPath(value)
    if ".." in path.parts or len(value) > 4096: raise ValueError("Archive path traversal or oversized name")
    for component in path.parts: name(component)
    return path.parts


@contextmanager
def parent_for(root, components):
    current = os.dup(root)
    try:
        for component in components:
            try: os.mkdir(component, 0o700, dir_fd=current)
            except FileExistsError: pass
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            os.close(current); current = child
        yield current
    finally: os.close(current)


@contextmanager
def archive(source):
    source = Path(source).absolute()
    with directory(source.parent) as parent:
        fd = os.open(source.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    stream = os.fdopen(fd, "rb")
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_INPUT:
            raise ValueError("Archive must be a regular file no larger than 256 MiB")
        if zipfile.is_zipfile(stream):
            stream.seek(0)
            with zipfile.ZipFile(stream) as handle:
                if len(handle.infolist()) > MAX_ENTRIES: raise ValueError("Too many archive entries")
                def entries():
                    for entry in handle.infolist():
                        kind = stat.S_IFMT(entry.external_attr >> 16)
                        if kind not in (0, stat.S_IFREG, stat.S_IFDIR): raise ValueError("Archive links/special files are forbidden")
                        if entry.compress_size and entry.file_size > entry.compress_size * 1000:
                            raise ValueError("Archive compression ratio exceeds the limit")
                        yield entry.orig_filename, entry.is_dir(), entry.file_size, entry
                yield entries(), handle.open
        else:
            stream.seek(0)
            magic = stream.read(6); stream.seek(0)
            try: handle = tarfile.open(fileobj=stream, mode="r:*")
            except tarfile.ReadError:
                if magic.startswith(b"\x1f\x8b"): suffix, decompressor = ".gz", lambda: gzip.GzipFile(fileobj=stream)
                elif magic == b"\xfd7zXZ\x00": suffix, decompressor = ".xz", lambda: lzma.LZMAFile(stream)
                else: raise ValueError("Unsupported or malformed archive; supported: ZIP, TAR, GZIP, XZ")
                stream.seek(0)
                filename = source.name[:-len(suffix)] if source.name.endswith(suffix) else source.name + "-unpacked"
                # Standalone streams have no trusted uncompressed length. Enforce
                # actual byte limits during extraction instead of trusting headers.
                yield iter([(filename, False, None, None)]), lambda _: decompressor()
                return
            with handle:
                def entries():
                    for entry in handle:
                        if not entry.isfile() and not entry.isdir(): raise ValueError("Archive links/special files are forbidden")
                        if entry.issparse(): raise ValueError("Sparse archive entries are not supported")
                        yield entry.name, entry.isdir(), entry.size, entry
                yield entries(), handle.extractfile
    finally: stream.close()


def extract(source, destination, token=None, selected=None):
    token = token or Token()
    destination = Path(destination).absolute(); name(destination.name)
    count = 0; total = 0; actual = 0; seen = set()
    selected = None if selected is None else set(selected)
    with transaction(destination.parent) as (target, temporary, _):
        os.mkdir("payload", 0o700, dir_fd=temporary)
        root = os.open("payload", os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=temporary)
        try:
            with archive(source) as (entries, opener):
                for entry_name, folder, size, entry in entries:
                    token.check(); count += 1; total += size or 0
                    components = parts(entry_name)
                    if count > MAX_ENTRIES or (size is not None and (size < 0 or size > MAX_FILE)) or total > MAX_TOTAL:
                        raise ValueError("Archive resource limit exceeded")
                    if not components and folder: continue
                    if not components or (components in seen and not folder): raise ValueError("Duplicate or empty archive filename")
                    seen.add(components)
                    if selected is not None and entry_name not in selected: continue
                    with parent_for(root, components[:-1]) as parent:
                        if folder:
                            try: os.mkdir(components[-1], 0o700, dir_fd=parent)
                            except FileExistsError:
                                existing = os.open(components[-1], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                                os.close(existing)
                            continue
                        output = os.open(components[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
                        written = 0
                        try:
                            with os.fdopen(output, "wb") as stream, opener(entry) as data:
                                while True:
                                    token.check()
                                    block = data.read(128 * 1024)
                                    if not block: break
                                    written += len(block); actual += len(block)
                                    if (size is not None and written > size) or written > MAX_FILE or actual > MAX_TOTAL:
                                        raise ValueError("Archive expanded beyond its declared resource limits")
                                    stream.write(block)
                                stream.flush(); os.fsync(stream.fileno())
                        except BaseException:
                            # fdopen owns the descriptor once entered; no user files are touched.
                            raise
                        if size is not None and written != size: raise ValueError("Truncated archive member")
            token.check()
            rename_no_replace(temporary, "payload", target, destination.name)
        finally: os.close(root)
    return str(destination)


def listing(source):
    result = []; total = 0
    with archive(source) as (entries, _):
        for entry_name, folder, size, _ in entries:
            parts(entry_name); total += size or 0
            if len(result) >= MAX_ENTRIES or (size is not None and (size < 0 or size > MAX_FILE)) or total > MAX_TOTAL: raise ValueError("Archive resource limit exceeded")
            result.append({"name": entry_name, "folder": folder, "size": size})
    return result


def create_zip(sources, destination, token=None, compressed=True, level=6):
    if type(level) is not int or not 0 <= level <= 9: raise ValueError("ZIP compression level must be 0–9")
    token = token or Token(); destination = Path(destination).absolute()
    sources = [Path(source).absolute() for source in sources]
    if not sources: raise ValueError("Select at least one source")
    for source in sources:
        if source.is_dir() and destination.is_relative_to(source): raise ValueError("Cannot create an archive inside a selected folder")
    seen = set(); count = 0
    with transaction(destination.parent) as (target, temporary, _):
        fd = os.open("payload", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=temporary)
        with os.fdopen(fd, "wb") as stream, zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED if compressed else zipfile.ZIP_STORED, compresslevel=level) as output:
            def add(parent, child, relative):
                nonlocal count
                token.check(); count += 1
                if count > MAX_ENTRIES: raise ValueError("Too many source entries")
                if relative in seen: raise ValueError("Duplicate archive source name")
                seen.add(relative)
                info = os.stat(child, dir_fd=parent, follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    output.writestr(relative + "/", b"")
                    source_fd = os.open(child, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                    try:
                        for item in os.listdir(source_fd): add(source_fd, item, relative + "/" + item)
                    finally: os.close(source_fd)
                elif stat.S_ISREG(info.st_mode):
                    source_fd = os.open(child, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
                    with os.fdopen(source_fd, "rb") as data, output.open(relative, "w") as member:
                        opened = os.fstat(data.fileno())
                        if not stat.S_ISREG(opened.st_mode): raise ValueError("Source type changed")
                        while True:
                            token.check(); block = data.read(128 * 1024)
                            if not block: break
                            member.write(block)
                        after = os.fstat(data.fileno())
                        if (opened.st_size, opened.st_mtime_ns) != (after.st_size, after.st_mtime_ns): raise ValueError("Source changed during compression")
                else: raise ValueError("Archive creation does not follow links or include special files")
            for source in sources:
                with directory(source.parent) as parent: add(parent, source.name, source.name)
        token.check(); rename_no_replace(temporary, "payload", target, destination.name)
    return str(destination)


def main():
    import resource
    import signal
    from fileops import Cancelled
    def cancelled(_signal, _frame): raise Cancelled("Archive operation cancelled")
    signal.signal(signal.SIGTERM, cancelled)
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (30, 30))
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("list", "extract", "create"))
    parser.add_argument("source")
    parser.add_argument("destination", nargs="?")
    parser.add_argument("extra", nargs="*")
    parser.add_argument("--level", type=int, default=6)
    args = parser.parse_args()
    if args.action == "list": result = listing(args.source)
    elif args.action == "extract":
        if not args.destination: parser.error("extract requires a fresh destination folder")
        result = extract(args.source, args.destination, selected=args.extra or None)
    else:
        if not args.destination: parser.error("create requires a destination ZIP")
        result = create_zip([args.source, *args.extra], args.destination, level=args.level)
    print(json.dumps(result))


if __name__ == "__main__":
    try: main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
