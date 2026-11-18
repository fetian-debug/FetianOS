"""Small user-owned preferences. Never persist passwords or auto-restore networks."""
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit


def default_path():
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "fetian-files/state.json"


def validate(value):
    bookmarks = []
    for uri in value.get("bookmarks", [])[:30]:
        if not isinstance(uri, str) or len(uri) > 4096: continue
        parsed = urlsplit(uri)
        if parsed.password is not None or parsed.query or parsed.fragment: continue
        if parsed.scheme in ("file", "smb", "sftp", "ftp", "dav", "davs", "mtp") and uri not in bookmarks: bookmarks.append(uri)
    tabs = [path for path in value.get("tabs", [])[:10] if isinstance(path, str) and len(path) <= 4096 and Path(path).is_absolute() and "\0" not in path]
    return {"bookmarks": bookmarks, "tabs": tabs, "theme": value.get("theme") if value.get("theme") in ("System", "Light", "Dark") else "System",
            "preview": value.get("preview", True) is True, "reduced_motion": value.get("reduced_motion", False) is True}


def load(path=None):
    path = path or default_path()
    try:
        if path.is_symlink() or path.stat().st_size > 65536: raise ValueError("Invalid preferences")
        value = json.loads(path.read_text())
        if not isinstance(value, dict): raise ValueError("Invalid preferences")
        return validate(value)
    except (OSError, ValueError, TypeError): return validate({})


def save(value, path=None):
    path = path or default_path(); path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=".state-", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(validate(value), stream); stream.flush(); os.fsync(stream.fileno())
            temporary.chmod(0o600); os.replace(temporary, path)
        finally: temporary.unlink(missing_ok=True)
