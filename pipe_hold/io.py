"""Strict, bounded input-file loading for synthetic traces."""

import json
import os
import stat

from .model import TraceError

MAX_BYTES = 262_144


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise TraceError("duplicate JSON object key")
        result[key] = value
    return result


def reject_constant(_text):
    raise TraceError("non-finite JSON number")


def load(path):
    fd = None
    try:
        if not stat.S_ISREG(os.lstat(path).st_mode):
            raise TraceError("input must be a stable regular file, not a symlink")
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as stream:
            fd = None
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise TraceError("input must be a regular file")
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise TraceError("input exceeds 262144 bytes")
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=reject_constant)
    except TraceError:
        raise
    except (OSError, ValueError, RecursionError):
        raise TraceError("cannot read a valid UTF-8 JSON trace") from None
    finally:
        if fd is not None:
            os.close(fd)
