#!/usr/bin/env python3
"""Decode a bounded raster thumbnail in a resource-limited subprocess."""
import base64
import json
import os
from pathlib import Path
import resource
import stat
import sys

from fileops import directory


def thumbnail(path):
    import gi
    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import GdkPixbuf
    path = Path(path).absolute()
    with directory(path.parent) as parent:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    with os.fdopen(fd, "rb") as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > 16 * 1024 * 1024:
            raise ValueError("Image preview requires a regular raster file up to 16 MiB")
        magic = source.read(16); source.seek(0)
        if not (magic.startswith((b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"GIF87a", b"GIF89a")) or (magic[:4] == b"RIFF" and magic[8:12] == b"WEBP")):
            raise ValueError("Preview supports PNG, JPEG, GIF and WebP; use the external viewer for other formats")
        loader = GdkPixbuf.PixbufLoader.new(); rejected = []
        def dimensions(loader, width, height):
            if width <= 0 or height <= 0 or width * height > 16 * 1024 * 1024 or max(width, height) > 16384:
                rejected.append(True)
            scale = min(1, 384 / max(1, width, height))
            loader.set_size(max(1, int(width * scale)), max(1, int(height * scale)))
        loader.connect("size-prepared", dimensions)
        total = 0
        try:
            while True:
                block = source.read(65536)
                if not block: break
                total += len(block)
                if total > 16 * 1024 * 1024: raise ValueError("Image input grew beyond limit")
                loader.write(block)
                if rejected: raise ValueError("Image pixel dimensions exceed preview limits")
            loader.close()
            after = os.fstat(source.fileno())
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns): raise ValueError("Image changed during preview")
            pixbuf = loader.get_pixbuf()
            if pixbuf is None or pixbuf.get_width() > 384 or pixbuf.get_height() > 384: raise ValueError("Invalid thumbnail")
            ok, data = pixbuf.save_to_bufferv("png", [], [])
            if not ok or len(data) > 1024 * 1024: raise ValueError("Thumbnail output limit exceeded")
            return {"png": base64.b64encode(data).decode("ascii"), "width": pixbuf.get_width(), "height": pixbuf.get_height()}
        except BaseException:
            try: loader.close()
            except Exception: pass
            raise


if __name__ == "__main__":
    try:
        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
        if len(sys.argv) != 2: raise ValueError("Select exactly one image")
        print(json.dumps(thumbnail(sys.argv[1])))
    except Exception as error:
        print(str(error), file=sys.stderr); sys.exit(1)
