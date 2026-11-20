"""Pure replay of successful descriptor operations; no OS process/pipe calls."""

from dataclasses import replace

from .model import (MAX_PIPES, MAX_PROCESSES, MAX_REFS, Ref, TraceError,
                    bounded_int, validate)


def _copy(ref, event, via, process, fd, *, cloexec=None):
    return Ref(ref.pipe, ref.side, ref.cloexec if cloexec is None else cloexec,
               event, via, process, fd, ref.created_event)


def _writers(tables, pipe):
    return [(process, fd, ref) for process in sorted(tables)
            for fd, ref in sorted(tables[process].items())
            if ref.pipe == pipe and ref.side == "write"]


def _holder(process, fd, ref):
    return {"process": process, "fd": fd, "cloexec": ref.cloexec,
            "created_event": ref.created_event, "via": ref.via,
            "source": (None if ref.source_process is None else {
                "process": ref.source_process, "fd": ref.source_fd,
                "created_event": ref.source_created_event})}


def audit(document, *, holders=8):
    """Return all check results with bounded writer evidence; never mutate input.

    A passing check means no modeled writers remain at that event, so EOF can be
    observed AFTER pending bytes drain. It is not an assertion of a real read.
    """
    bounded_int(holders, 0, 32, "holders")
    root, events = validate(document)
    tables = {root: {}}
    process_names = {root}
    pipes = set()
    checks = []
    for number, event in enumerate(events, 1):
        op, process = event["op"], event["process"]
        try:
            if process not in tables:
                raise TraceError("process is unknown or has exited")
            table = tables[process]

            def descriptor(fd):
                if fd not in table:
                    raise TraceError("descriptor is not open in this process")
                return table[fd]

            if op == "pipe":
                read_fd, write_fd = event["read_fd"], event["write_fd"]
                if event["pipe"] in pipes or len(pipes) == MAX_PIPES:
                    raise TraceError("pipe name reused or 16-pipe lifetime limit exceeded")
                if read_fd == write_fd or read_fd in table or write_fd in table:
                    raise TraceError("pipe requires two distinct free descriptors")
                pipes.add(event["pipe"])
                for fd, side in ((read_fd, "read"), (write_fd, "write")):
                    table[fd] = Ref(event["pipe"], side, event["cloexec"], number, "pipe")
            elif op == "fork":
                child = event["child"]
                if child in process_names or len(process_names) == MAX_PROCESSES:
                    raise TraceError("child name reused or 32-process lifetime limit exceeded")
                process_names.add(child)
                tables[child] = {fd: _copy(ref, number, "fork", process, fd)
                                 for fd, ref in table.items()}
            elif op == "dup2":
                source = descriptor(event["src"])
                if event["src"] != event["dst"]:
                    # Atomic replacement in this serialized model. Self-dup2 is
                    # a true no-op, including the close-on-exec flag/provenance.
                    table[event["dst"]] = _copy(source, number, "dup2", process,
                                                event["src"], cloexec=False)
            elif op == "close":
                descriptor(event["fd"])
                del table[event["fd"]]
            elif op == "set_cloexec":
                ref = descriptor(event["fd"])
                table[event["fd"]] = replace(ref, cloexec=event["value"])
            elif op == "exec":
                tables[process] = {fd: ref for fd, ref in table.items() if not ref.cloexec}
            elif op == "exit":
                del tables[process]
            elif op == "expect_eof":
                ref = descriptor(event["fd"])
                if ref.side != "read":
                    raise TraceError("expect_eof requires a read-end descriptor")
                writers = _writers(tables, ref.pipe)
                checks.append({"event": number, "process": process, "fd": event["fd"],
                               "pipe": ref.pipe, "eof_after_drain": not writers,
                               "writer_descriptors": len(writers),
                               "writer_processes": len({p for p, _, _ in writers}),
                               "self_held_writers": sum(p == process for p, _, _ in writers),
                               "holders": [_holder(p, fd, r) for p, fd, r in writers[:holders]],
                               "omitted_holders": max(0, len(writers) - holders)})
            if sum(len(t) for t in tables.values()) > MAX_REFS:
                raise TraceError("256-live-descriptor limit exceeded")
        except TraceError as exc:
            raise TraceError(f"event {number}: {exc}") from None
    failed = sum(not check["eof_after_drain"] for check in checks)
    final = []
    for pipe in sorted(pipes):
        readers = sum(ref.pipe == pipe and ref.side == "read"
                      for table in tables.values() for ref in table.values())
        writers = len(_writers(tables, pipe))
        final.append({"pipe": pipe, "read_descriptors": readers,
                      "write_descriptors": writers, "no_writers": writers == 0})
    return {"schema_version": 1, "events": len(events), "checks": checks,
            "checks_total": len(checks), "failed_checks": failed,
            "holder_limit": holders, "gate_failed": failed > 0,
            "alive_processes": len(tables),
            "live_descriptors": sum(len(t) for t in tables.values()), "final_pipes": final}
