# x86-64 TLB assembly notes

## Scope

This document is a compact architecture note for x86-64 invalidation instructions and how they relate to the observability goals of this repository.

It is not a recommendation to issue raw invalidation instructions from arbitrary kernel code.

## `invlpg`

`invlpg` invalidates a translation for a single linear address on the local CPU.

Operationally:

- it is privileged
- it is local unless combined with wider kernel shootdown machinery
- it is often the easiest instruction to discuss in educational probes

For this repository, `arch-probes/x86_64/invlpg_probe.h` exposes a tiny wrapper only to make the instruction concrete in a lab module.

## `invpcid`

`invpcid` is more expressive than `invlpg` because it can invalidate based on PCID-aware context and operation type.

Important caveats:

- availability depends on CPU feature support
- semantics depend on the operation type
- it interacts with PCID-aware address-space handling
- it should not be treated as a drop-in replacement for kernel TLB helpers

The repository therefore keeps `invpcid` as a guarded sketch rather than an active default demo.

## PCID

PCID allows TLB entries to be tagged by process-context identifier so that some context switches and CR3 transitions preserve more useful translation state.

That does not remove the need for invalidation. It changes which state can remain valid and how aggressively the CPU must discard translations on context changes.

## CR3 reloads

CR3 reload behavior matters because it is one of the historic control points for address-space switching and translation state effects. With PCID-aware behavior, a CR3 write does not always mean the same thing it did on older systems.

For observability work, the practical lesson is:

- instruction choice matters
- context tagging matters
- the effective translation disruption path is more nuanced than a single “flush happened” label

## Relevant kernel locations

- `arch/x86/kernel/head_64.S`
- `arch/x86/mm/tlb.c`

This repository does not modify early boot at this stage. The note is included to help orient future instrumentation work.
