#!/usr/bin/env python3
"""Select only completed release bundles, or an explicitly checksummed legacy ISO."""
import json
from pathlib import Path
import sys


def select(output):
    candidates = []
    for record in output.glob("*/build.json"):
        if record.parent.name.startswith("."): continue
        try:
            metadata = json.loads(record.read_text())
            name = metadata["iso"]["file"]
            if Path(name).name != name or not metadata["verification"]["image_static_checks"]: continue
            path = record.parent / name
            if path.is_file() and (record.parent / (name + ".sha256")).is_file(): candidates.append(path)
        except (OSError, ValueError, KeyError): continue
    candidates.extend(path for path in output.glob("*.iso") if path.is_file() and Path(str(path) + ".sha256").is_file())
    if not candidates: raise ValueError("No completed, checksummed image found")
    return max(candidates, key=lambda path: path.stat().st_mtime_ns)


if __name__ == "__main__":
    try: print(select(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "output"))
    except (OSError, ValueError) as error: sys.exit(str(error))
