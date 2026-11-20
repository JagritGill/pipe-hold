# pipe-hold

Explain which inherited or duplicated pipe writers keep a reader from reaching
EOF after buffered data drains. Replay a small **synthetic descriptor trace** and
turn an EOF expectation into concrete process/descriptor holders and provenance.
Useful for learning pipeline lifecycle bugs and keeping those assumptions in
regression fixtures. No commands, live process inspection or real pipes are run.

The demo's producer exits, but the shell still owns a writer. A reader's EOF
expectation fails. Closing that last writer fixes a later expectation; the report
retains the earlier failure. A second example shows a dup2 alias surviving exec
after the original close-on-exec writer disappears.

## Quickstart

Use installed Python 3.13+ from this folder; no install or dependencies:

```sh
python3 -B -m pipe_hold examples/parent-hold.json
python3 -B -m pipe_hold examples/exec-alias.json --format json
python3 -B -m pipe_hold examples/closed.json
```

First two commands intentionally exit **1** (an EOF expectation is held); the
closed example exits **0**. Exact first-command output:

```text
events=10 checks=2 failed=1
event=8 reader:3 pipe=output after_drain=HELD writers=1 self_held=0
  holder=shell:4 created_event=1 via=pipe cloexec=false
event=10 reader:3 pipe=output after_drain=PASS writers=0 self_held=0
gate=FAIL (EOF expectations held)
```

`--holders 0` suppresses holder evidence without changing exact counts or the gate.
Default eight, maximum 32, holders per check. Every check is reported; omissions
inside a check are counted. JSON adds copy provenance: the source process/fd and
the event that created that source reference. Names and fd numbers are synthetic
labels, not discovered PIDs or kernel descriptors.

## Trace format

Top level is exactly `{"root": "shell", "events": [...]}`. Root starts alive with
an **empty modeled descriptor table**; stdin/stdout/stderr are not precreated.
Events are ordered, atomic, successful model operations. Every event requires
`op` and `process`, plus exactly these fields:

| Operation | Additional fields | Effect |
| --- | --- | --- |
| `pipe` | `pipe`, `read_fd`, `write_fd`, `cloexec` | Fresh pipe at two explicit free slots; same initial flag on both |
| `fork` | `child` | Copy all references/flags into a fresh child table |
| `dup2` | `src`, `dst` | Replace destination with source endpoint; clear its close-on-exec flag |
| `close` | `fd` | Remove one reference |
| `set_cloexec` | `fd`, `value` | Change only that descriptor's flag |
| `exec` | none | Model successful exec: close flagged descriptors |
| `exit` | none | Remove this process and all its references; children survive |
| `expect_eof` | `fd` | Require a read end; check no modeled writers remain |

`dup2` with equal valid source/destination is a true no-op, including its flag and
provenance. Replacing a different destination releases the old reference. Invalid
source, unopened close, reused child/pipe name, wrong endpoint or exited process
is an error, not a simulated failed syscall. Explicit pipe slots are caller-supplied
abstractions, not the OS's lowest-free descriptor allocation rule.

Names: 1..32 ASCII letters/digits/underscore/hyphen, starting with a letter.
Descriptors: integers 0..63, not Booleans. Flags: JSON Booleans. Bounds: 512 events,
32 lifetime process names, 16 lifetime pipe names, 256 live references and 1..64
EOF checks. File input is at most 256 KiB, UTF-8 JSON in a stable regular file.
Symlinks/special files, duplicate JSON fields and non-finite numbers are rejected.

Exit **0**: all supplied EOF expectations pass. Exit **1**: at least one fails,
even if repaired later. Exit **2**: invalid trace/input/usage; no partial stdout
report. This is not an automatic leak detector: an open writer without a supplied
EOF expectation is not a finding.

## API and verification

```python
from pipe_hold import audit

report = audit({"root": "reader", "events": [
    {"op": "pipe", "process": "reader", "pipe": "p",
     "read_fd": 3, "write_fd": 4, "cloexec": False},
    {"op": "close", "process": "reader", "fd": 4},
    {"op": "expect_eof", "process": "reader", "fd": 3},
]})
assert not report["gate_failed"]
```

`audit` returns JSON-compatible data, does not mutate input and raises `TraceError`
for an invalid model. Validate the complete trace before trusting any result.

```sh
python3 -B -m unittest discover -s tests -v
python3 -B scripts/check_examples.py
python3 -B scripts/check_release.py
git diff --check
```

Local targets: CPython 3.13.5 and 3.15.0; CI matrix 3.13/3.15. Tests include an
independent lifetime definition over six inherited aliases, actual CLI invocations,
limits and invalid inputs. No static checker/full linter is configured; syntax
parsing is neither. The release scan checks exact inventory, links and selected
credential/private-path patterns; it cannot guarantee security or provenance.

## Limits

**PASS means EOF after pending bytes drain, not that a read returns zero now.**
There is no byte buffer, I/O, capacity, signal, scheduler, thread/shared-fd-table,
SCM_RIGHTS, failed exec, privilege transition or real kernel model. No FIFO reopen,
file/socket endpoint, OS trace importer or live process control. All modeled
references must be represented; omitted inherited writers make conclusions
incomplete. A retained writer is evidence for this supplied expectation, not a
proof of deadlock or an instruction to close it in a real application. Reports
contain supplied names and structural metadata; they are not anonymized.

See [architecture/tradeoffs](docs/architecture.md), [related work](docs/related-work.md),
[agent guidance](AGENTS.md), [attribution](NOTICE.md) and [MIT license](LICENSE).
