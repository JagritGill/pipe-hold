# Related work and independent scope

Research: November 20, 2026, before implementation. Searches included
`pipe EOF file descriptor reference count simulator fork dup close tool`,
`github pipe file descriptor lifecycle simulator EOF inherited writer`,
`file descriptor visualization fork dup2 pipes simulator`,
`pipe EOF descriptor trace analyzer offline tool`, and the tentative names
`pipe-lifeline` and `pipe-hold`. Local catalog and public personal repository
names were checked; searches do not establish global novelty or name availability.

An initial weighted-quorum migration idea was rejected before code because
[MoonQuorum](https://mooncakes.io/docs/JingLan0v0/quorum%400.2.0) already closely
covered the proposed checks. The implemented project has a different subject.

## Closest alternatives

- [OSVisualizationTool](https://github.com/ethan-fong/OSVisualizationTool) is the
  closest broad comparator. Its README describes live Linux process/file-table
  views and reference reconstruction from strace. **Descriptor inheritance and
  reference ownership substantially overlap.** Here the narrower artifact is a
  deterministic offline regression report for explicit after-drain EOF checks,
  without launching, observing or controlling a process.
- [unix-pipeline-executor](https://github.com/John-Paul-Alvarez/unix-pipeline-executor)
  executes C++ pipelines using fork/dup2/exec and explains unused-end closure.
  This project accepts synthetic event data; it neither executes commands nor
  captures actual system calls.
- [xv6 Lab's pipe inheritance lesson](https://snowch.github.io/xv6-lab/lessons/fork-inherits-pipe-ends/)
  teaches why retained writer references delay EOF and runs programs in xv6.
  This is an established concept, not a new discovery. Our fixture/check format
  makes those lifecycle assumptions repeatable without a VM or kernel build.

These comparisons use published primary READMEs/documentation, not exhaustive
feature evaluations. No claim that alternatives lack any feature or that the
project is globally unique. Valgrind's core manual was attempted but returned
503; it is not used to substantiate a detailed comparison.

## Semantics and attribution

Primary [pipe](https://man7.org/linux/man-pages/man7/pipe.7.html),
[dup2](https://man7.org/linux/man-pages/man2/dup.2.html),
[fork](https://man7.org/linux/man-pages/man2/fork.2.html) and
[exec](https://man7.org/linux/man-pages/man2/execve.2.html) manuals were consulted.
Pipe EOF depends on writer references and drainage, forks copy descriptor
references, non-self dup2 replaces its destination and clears close-on-exec,
self dup2 does nothing, and successful exec closes marked descriptors. We model
only those selected structural rules; not buffering, signals, scheduling,
threads, failed syscalls, privilege transitions or an entire OS.

The primary demo exits the producer while a shell still owns a writer. The
reader's EOF expectation fails and names that holder. Closing it makes a later
expectation pass, without erasing the earlier failure. A second fixture exposes
a dup2 alias that survives exec after the original close-on-exec writer closes.

Implementation, synthetic fixtures and tests were independently written with
AI assistance. No comparator code, test, fixture or documentation wording was
copied or translated; no application was cloned. No private/employer/customer
source or process trace is used. Standard-library runtime only. Routine portfolio
release/CI conventions are credited in [NOTICE](../NOTICE.md).
