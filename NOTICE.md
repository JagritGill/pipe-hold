# Attribution and dependencies

Original implementation, fixtures and tests were written with AI assistance for
this portfolio project. [MIT](LICENSE) covers original files and is not a claim
of sole human authorship or a relicensing of other projects.

Runtime uses Python's standard library only, provided under the
[Python licensing terms](https://docs.python.org/3/license.html). No third-party
package or source is bundled. Established descriptor/EOF semantics and primary
comparison sources are credited in [related work](docs/related-work.md).
No comparator implementation or fixture was copied or translated.

Routine portfolio release/inventory conventions and previously verified CI pins
are reused with attribution here; the lifecycle implementation and examples are
independently written. CI invokes MIT-licensed external dependencies
[actions/checkout](https://github.com/actions/checkout) and
[actions/setup-python](https://github.com/actions/setup-python) at pinned commits;
their source is not vendored or relicensed. A workflow definition is not evidence
of a passing run: consult checks for the exact commit.
