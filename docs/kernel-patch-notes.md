# Kernel Patch Notes

## Framing

These patches are lab artifacts for observability work on Linux 6.6+ style trees. They are intentionally scoped around measurement and attribution, not around changing MM behavior for performance gain.

This repository should be read as:

- a research and debugging lab
- an instrumentation starting point
- a way to make hidden MMU activity more observable

It should not be read as:

- an upstream-ready patch series
- a claim that these hooks are already validated across kernel versions
- a promise of direct throughput improvement

## Patch summary

### 0001: x86 TLB invalidation tracepoint

Adds an x86-local tracepoint in `arch/x86/mm/tlb.c` for invalidation ranges.

Captured fields:

- `pid`
- `tgid`
- `comm`
- `start`
- `end`
- `range_size`
- `target_cpu_count`
- `broadcast`

Notes:

- `target_cpu_count` is a best-effort count derived from the cpumask in scope
- `broadcast` is a hint field, not a proof that a hardware-assisted path was used
- the event is meant to be cheap enough for short capture windows, not always-on fleet telemetry

### 0002: MMU notifier invalidation tracepoint

Adds notifier range events for start and end phases in `mm/mmu_notifier.c`.

Purpose:

- correlate notifier clients with invalidation bursts
- expose a join point between MMU activity and GPU UVM or RDMA-adjacent control paths

Notes:

- this is attribution instrumentation, not subsystem blame assignment
- notifier activity and TLB invalidation can correlate without being the sole cause of a latency event

### 0003: Experimental `/proc/<pid>/tlb_stats` sketch

This patch is deliberately framed as a sketch rather than a production-ready implementation.

Why:

- adding process-local counters to `mm_struct` is invasive
- exact in-kernel attribution has real maintenance and overhead tradeoffs
- userspace aggregation from tracepoints is the preferred default for this lab

The patch therefore documents one possible procfs shape and explicitly warns that a real implementation would need more design work before it is credible for wider use.

### 0004: Broadcast invalidation capability exposure

Adds a small sysfs view of CPU capability indicators related to hardware-assisted invalidation support.

Important:

- it does not implement `INVLPGB`
- it does not claim that any given flush path used broadcast invalidation
- it only exposes whether the running CPU advertises the relevant feature bit

### 0005: x86 architecture-context invalidation sketch

Extends the x86 tracepoint sketch with architecture-flavored fields such as:

- range size in pages
- local-versus-remote invalidation scope
- a best-effort instruction-family classification

Notes:

- the instruction-family field is heuristic, not a hardware proof
- the sketch is intended to show where such attribution could live in `arch/x86/mm/tlb.c`
- this is explicitly research material, not an upstream-ready ABI

### 0006: arm64 TLBI observability sketch

Shows a plausible arm64 hook point around `__flush_tlb_range()` in `arch/arm64/include/asm/tlbflush.h`, with trace fields for:

- TLBI scope
- range size in pages
- barrier-phase markers

Notes:

- the arm64 low-level invalidation paths live primarily in headers and inline helpers, which is why this sketch touches `tlbflush.h`
- the patch is framed as a sketch because tracepoint plumbing through low-level arm64 code needs careful per-tree review
- barrier markers are intended for attribution, not for making timing claims on their own

## Overhead considerations

The patches are written with these constraints in mind:

- avoid formatting-heavy work in hot paths
- prefer tracepoints over new in-kernel accounting state
- keep instrumentation local to investigation windows
- separate capability exposure from behavioral claims

## Recommended deployment model

For real debugging work:

1. start with `0001`, `0002`, and `0004`
2. treat `0003` as a design note unless you explicitly want to prototype procfs exposure
3. treat `0005` and `0006` as architecture-context sketches, not default patches to apply
4. collect traces during narrow intervals
5. aggregate in userspace
6. correlate against latency, scheduler, and workload metrics before drawing conclusions
