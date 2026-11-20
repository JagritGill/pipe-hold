# Architecture and invariants

`model.py` validates the small event grammar, scalar types, names and bounds.
`core.py` replays events into per-process descriptor dictionaries of immutable
references. Each reference has a pipe identity, endpoint side, per-descriptor
close-on-exec flag, creation event and immediate copy source. Copy provenance
refers to a specific source creation event, so descriptor number reuse does not
silently identify a later unrelated reference. Flag changes preserve birth data.

Fork copies references with independent flags; aliases still name the same pipe
endpoint. Successful exec drops only flagged references. Exit drops that table.
Non-self dup2 replaces a destination atomically and clears its flag; self dup2
does nothing. Pipe names and process names are unique over the trace lifetime,
while a closed fd slot may be reused. No kernel descriptors are touched.

At an EOF check, scan all live descriptors for writers of the reader's pipe.
Zero writers means EOF is available **after drainage**. Otherwise record exact
writer-descriptor, process and self-held counts, and a bounded witness list sorted
by process name then numeric fd. Witnesses are copied into result data, so later
closes cannot alter earlier evidence. Every supplied check remains in the report;
later repair cannot erase an earlier gate failure. Caps affect witnesses only.

The final summary counts live endpoint references, including zero-reference
pipes retained by name for trace history. `no_writers` is structural, not a read
result; a pipe with no readers cannot actually be read. No partial result escapes
if a later event is invalid. Replay state is local to each API call, never input
mutation. `io.py` provides bounded local JSON loading; `__main__.py` formats output.

Time is bounded by event-count times live descriptors, plus deterministic holder
sorting. Memory includes live tables and at most 64 checks with 32 holders each.
Bounds are explicit: 512 events, 32 process names, 16 pipe names, 256 references,
64 fd slots/process, 256 KiB file. These are design limits, not performance claims.
File type is checked before and after open; this is not protection against every
hostile concurrent filesystem change. Use trusted stable local files.

This intentionally trades OS breadth for a small explainable lifecycle model.
It does not simulate byte availability or whether an actual operation blocks.
Independent lifetime tests describe survivor sets without replaying the core's
nested-table algorithm. Boundary tests separately exercise replacement, copying,
flags, process exit, resource limits and provenance. Actual CLI tests verify
expected findings versus invalid input. No real-process/pipe integration claim.

See [README](../README.md), [research](related-work.md) and [agent guide](../AGENTS.md).
