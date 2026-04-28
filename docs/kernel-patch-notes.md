# Kernel Patch Notes

## Intent

These patches are designed as observability-first lab artifacts for Linux 6.6+ style trees. They prefer tracepoints and capability exposure over behavioral modification.

## Patch summary

### 0001: x86 TLB invalidation tracepoint

Adds a low-overhead tracepoint near the invalidation path in `arch/x86/mm/tlb.c`.

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

- intended to avoid expensive formatting
- range size is derived once
- fanout is best-effort and cheap

### 0002: MMU notifier invalidation tracepoint

Adds notifier range events for start and end phases in `mm/mmu_notifier.c`.

Purpose:

- correlate notifier clients with invalidation bursts
- make GPU UVM and RDMA-adjacent activity easier to attribute

### 0003: Experimental per-process `/proc/<pid>/tlb_stats`

This is intentionally the least preferred mechanism in the repo.

Why:

- modifying `mm_struct` is invasive
- maintaining exact per-process counts inside the kernel can distort the thing being measured
- tracepoint aggregation in userspace is usually a cleaner default

The patch is included as a sketch because teams sometimes want a low-friction process-local readout for ad hoc debugging.

### 0004: Broadcast invalidation capability exposure

Adds a small sysfs view of CPU capabilities relevant to hardware-assisted broadcast invalidation support.

Important:

- no new invalidation mechanism is implemented
- no new instruction path is claimed
- this is capability exposure only

## Overhead considerations

The patches are written with the following constraints:

- no heavy string formatting in hot paths
- no dynamic allocation in invalidation paths
- no attempt at exact in-kernel attribution beyond the experimental sketch
- default preference for tracepoints that can be turned on only during investigation

## Recommended deployment model

For production investigation:

1. apply tracepoint patches first
2. leave experimental `/proc` patch out unless needed
3. collect traces for focused windows
4. aggregate in userspace
5. correlate with latency, scheduler, and workload metrics
