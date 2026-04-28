# Architecture probe modules

This directory contains small out-of-tree kernel module examples for architecture-specific TLB invalidation instructions and sequences.

These files are intentionally educational and instrumentation-oriented.

They are not:

- replacements for Linux MM code
- recommendations to bypass kernel TLB helpers
- stress tools
- production kernel modules

They are intended to show where architecture-specific invalidation instructions live and how to discuss them safely in the context of observability work.

## Safety

Use only on lab machines, VMs, or disposable test kernels.

- the x86-64 example allocates one page, touches it, executes a single educational invalidation wrapper, and unloads cleanly
- the arm64 example defaults to notes-only behavior and does not execute TLBI by default
- Linux already has correct, architecture-aware TLB maintenance helpers in its MM code; these probes are not substitutes

## Build model

Each subdirectory uses a standard out-of-tree module Makefile against:

```text
/lib/modules/$(uname -r)/build
```

That means the build requires matching kernel headers for the running kernel.
