#!/usr/bin/env python3
"""Bounded owned-fixture pressure producer; caller attaches cgroup before gate."""
import errno
import json
import os
import signal
import sys
import time


def main():
    kind = sys.argv[1]
    print("READY", flush=True)
    if sys.stdin.readline().strip() != "ATTACHED":
        raise SystemExit("resource gate not opened")
    children, blocks = [], []
    try:
        if kind == "memory":
            for _ in range(192):
                blocks.append(bytearray(1024 * 1024))
            print(json.dumps(dict(allocated_bytes=len(blocks) * 1024 * 1024)), flush=True)
        else:
            denied = False
            for _ in range(3 if kind == "cpu" else 12):
                try:
                    pid = os.fork()
                except OSError as error:
                    if error.errno != errno.EAGAIN:
                        raise
                    denied = True
                    break
                if pid == 0:
                    end = time.monotonic() + 2
                    while time.monotonic() < end:
                        if kind == "pids":
                            time.sleep(.01)
                    os._exit(0)
                children.append(pid)
            print(json.dumps(dict(children=len(children), fork_denied=denied)), flush=True)
            for pid in children:
                os.waitpid(pid, 0)
            children.clear()
    finally:
        for pid in children:
            try:
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
            except ProcessLookupError:
                pass


if __name__ == "__main__":
    main()
