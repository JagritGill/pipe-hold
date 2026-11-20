# Working on pipe-hold

Purpose: explain synthetic descriptor holders that prevent EOF after pipe drainage.
Read [README](README.md), [architecture](docs/architecture.md), and
[research](docs/related-work.md). This is not a live OS tracer or deadlock proof.

Map: `model.py` validates grammar/bounds; `core.py` replays immutable references
inside process tables; `io.py` loads bounded JSON; `__main__.py` formats output.
`examples/` are synthetic; `tests/` cover independent survivor definitions, actual
CLI and release guards; `scripts/` verify examples and publication scope.

Commands from this folder, using installed Python; no install step:

```sh
python3 -B -m unittest discover -s tests -v
python3.13 -B -m unittest discover -s tests -v
python3 -B scripts/check_examples.py
python3 -B scripts/check_release.py
python3 -B scripts/check_release.py --json
python3 -B -m pipe_hold examples/parent-hold.json
git diff --check
```

Parent-hold/exec-alias examples intentionally exit 1; closed exits 0; invalid input
exits 2 without partial stdout. Local targets are Python 3.13.5/3.15.0. No static
checker/full linter configured; syntax checks are neither. Record actual run
results and exact commit in the handoff, not assumed success from this list.

Invariants: references, not process intent, determine writer ownership. Fork flags
are independently mutable; non-self dup2 clears destination CLOEXEC and replaces
its prior reference; self-dup2 is a no-op. Successful exec closes only marked fds.
Exit closes one table, not children. Pipe/process names are lifetime unique.
Creation provenance distinguishes fd reuse. Counts/gate ignore witness caps.
Historical failures survive repair. EOF claims always say after drainage.

Preserve owner work and unrelated repositories. Use original synthetic traces and
independent definitions/real CLI regressions for semantic changes. Do not add live
tracing, process control, hardware, private data, paid tools, CodeRabbit/external
reviewers, credentials or security changes. Publication needs applicable task
authorization; never bypass CI or permissions. Keep machine-specific evidence
outside release. Handoff with dirty files, exact commit, tests/exits, observed CI,
unrun checks and limits. Update inventory/docs with scope changes; see
[NOTICE](NOTICE.md) and [LICENSE](LICENSE) before adding third-party material.
