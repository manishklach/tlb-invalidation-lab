# arm64 TLB assembly notes

## Scope

This document summarizes arm64 TLBI concepts that matter for observability and careful lab-oriented instrumentation.

It is not a recommendation to emit raw TLBI from normal kernel code paths outside the architecture's established MM helpers.

## TLBI

arm64 invalidation is expressed through TLBI operations, with many variants depending on:

- address space or ASID scope
- page versus broader context invalidation
- local versus inner-shareable versus wider visibility

## Barrier discipline

The classic educational sequence is:

```asm
dsb ishst
tlbi ...
dsb ish
isb
```

The exact sequence used by the kernel depends on operation semantics, but the general lesson is stable: barriers are part of correctness, not optional decoration.

## ASID

ASIDs on arm64 play a role analogous to tagged address-space handling on other architectures: they help preserve and distinguish translation state across contexts.

That means observability work on arm64 should care about more than “a flush happened.” Useful questions include:

- what TLBI scope was used
- whether the invalidation was local or inner-shareable
- how range-oriented the invalidation was
- where barriers occurred around the sequence

## Local versus inner-shareable

From an observability perspective, local versus inner-shareable invalidation is especially relevant because it changes how much of the machine is involved in maintaining correctness.

That can affect:

- fanout
- latency sensitivity
- correlation with scheduler and tail-latency symptoms

## Relevant kernel locations

- `arch/arm64/kernel/head.S`
- `arch/arm64/mm/`

This repository does not modify early boot at this stage. These references are included to anchor future architecture-aware observability work.
