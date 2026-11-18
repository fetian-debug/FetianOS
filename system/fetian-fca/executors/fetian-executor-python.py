#!/usr/bin/python3
"""Trusted sum-i64 ABI v1 executor. No authority store or filesystem API."""
import json
import struct
import sys

MAX_FRAME = 65536


def exact(size):
    result = bytearray()
    while len(result) < size:
        data = sys.stdin.buffer.read(size - len(result))
        if not data:
            raise ValueError("truncated frame")
        result.extend(data)
    return bytes(result)


def read():
    size = struct.unpack(">I", exact(4))[0]
    if not 0 < size <= MAX_FRAME:
        raise ValueError("frame limit")
    return json.loads(exact(size))


def write(value):
    data = json.dumps(value, separators=(",", ":"), allow_nan=False).encode()
    if not 0 < len(data) <= MAX_FRAME:
        raise ValueError("frame limit")
    sys.stdout.buffer.write(struct.pack(">I", len(data)) + data)
    sys.stdout.buffer.flush()


def main():
    start = read()
    if start["version"] != 1 or start["workload"] != "fetian.sum-i64/v1":
        raise ValueError("unsupported ABI")
    credential, checkpoint = start["credential"], start["checkpoint"]
    sequence = 0

    def request(operation, **arguments):
        nonlocal sequence
        sequence += 1
        write(dict(version=1, request_id=sequence, operation=operation,
                   arguments=dict(credential=credential, **arguments)))
        response = read()
        if set(response) != {"version", "request_id", "result", "error"}:
            raise ValueError("unknown response fields")
        if response["version"] != 1 or response["request_id"] != sequence:
            raise ValueError("response ordering/version")
        if response["error"] is not None:
            raise ValueError(response["error"]["code"])
        return response["result"]

    request("hello", workload="fetian.sum-i64/v1")
    while True:
        chunk = request("read", position=checkpoint["next_input_position"])
        if not chunk["values"]:
            request("complete")
            return
        total = checkpoint["accumulated_result"]
        for value in chunk["values"]:
            if type(value) is not int:
                raise ValueError("integer required")
            total += value
            if not -(2**63) <= total < 2**63:
                raise ValueError("SUM_OVERFLOW")
        next_chunk = checkpoint["last_committed_chunk"] + 1
        progress = dict(sequence=next_chunk,
                        input_position=checkpoint["next_input_position"],
                        next_input_position=chunk["next_input_position"],
                        accumulated_result=total,
                        idempotency_key=f"chunk-{next_chunk}")
        checkpoint = request("commit", progress=progress)["checkpoint"]
        if start.get("barrier_after") == checkpoint["last_committed_chunk"]:
            request("barrier")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as error:
        print(f"executor failure: {type(error).__name__}", file=sys.stderr)
        raise SystemExit(1)
