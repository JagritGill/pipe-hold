"""The input grammar contains data, never commands or real process IDs."""

from dataclasses import dataclass
import re

MAX_EVENTS = 512
MAX_PROCESSES = 32
MAX_PIPES = 16
MAX_REFS = 256
MAX_CHECKS = 64

FIELDS = {
    "pipe": {"pipe", "read_fd", "write_fd", "cloexec"},
    "fork": {"child"}, "dup2": {"src", "dst"},
    "close": {"fd"}, "set_cloexec": {"fd", "value"},
    "exec": set(), "exit": set(), "expect_eof": {"fd"},
}


class TraceError(ValueError):
    """Invalid trace or exceeded model bound."""


def bounded_int(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise TraceError(f"{name} must be an integer in [{low}, {high}]")
    return value


def name(value):
    if type(value) is not str or re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,31}", value) is None:
        raise TraceError("names must be 1..32 ASCII letters/digits/_/-, beginning with a letter")
    return value


def validate(document):
    if type(document) is not dict or set(document) != {"root", "events"}:
        raise TraceError("expected exactly root and events")
    root = name(document["root"])
    events = document["events"]
    if type(events) is not list or not 1 <= len(events) <= MAX_EVENTS:
        raise TraceError("events must contain 1..512 entries")
    copied = []
    checks = 0
    for number, event in enumerate(events, 1):
        try:
            if type(event) is not dict or type(event.get("op")) is not str or event["op"] not in FIELDS:
                raise TraceError("unknown event operation")
            op = event["op"]
            if set(event) != {"op", "process"} | FIELDS[op]:
                raise TraceError("event fields do not match operation")
            name(event["process"])
            for key in ("child", "pipe"):
                if key in event:
                    name(event[key])
            for key in ("fd", "src", "dst", "read_fd", "write_fd"):
                if key in event:
                    bounded_int(event[key], 0, 63, key)
            for key in ("cloexec", "value"):
                if key in event and type(event[key]) is not bool:
                    raise TraceError(f"{key} must be boolean")
            checks += op == "expect_eof"
            copied.append(dict(event))
        except TraceError as exc:
            raise TraceError(f"event {number}: {exc}") from None
    if not 1 <= checks <= MAX_CHECKS:
        raise TraceError("trace must contain 1..64 expect_eof events")
    return root, copied


@dataclass(frozen=True)
class Ref:
    pipe: str
    side: str
    cloexec: bool
    created_event: int
    via: str
    source_process: str | None = None
    source_fd: int | None = None
    source_created_event: int | None = None
