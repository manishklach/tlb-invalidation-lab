# AI Inference Impact

## Why a mostly GPU-bound stack still cares about CPU MMU behavior

Inference clusters often look GPU-bound from the outside, but the supporting path is not GPU-only. CPU threads still manage:

- runtime orchestration
- DMA setup and teardown
- networking
- pinned memory coordination
- memory-mapped artifacts
- process lifecycle and allocator behavior

If those CPU threads are repeatedly interrupted by translation invalidation work, the effect can propagate into user-visible inference latency. This repository is aimed at making that possibility measurable enough to investigate, not at treating it as a universal explanation.

## Common trigger patterns

### Pinned memory and DMA staging

Pinned host memory is normal in accelerator systems. Pinning, unpinning, remapping, and subsystem coordination can increase MMU activity around regions that matter to data movement.

### GPU UVM and MMU notifier clients

Unified or semi-unified memory paths often depend on notifier-driven invalidation coordination. Even when the main work happens on accelerators, the invalidation control path often begins on the CPU.

### RDMA buffers

Registration and teardown of RDMA-addressable regions can produce memory-management churn, especially in dynamic or multi-tenant serving environments.

### KV-cache-adjacent state and memory-mapped artifacts

Large serving systems frequently rely on memory-mapped files, shared metadata, model fragments, or local caches. If those mappings churn or are rotated aggressively, the cost can spill into translation maintenance.

### Allocator pressure

Protection changes, reclamation, mapping churn, and short-lived regions can all create invalidation-heavy patterns even without a single dramatic failure event.

## Why the tail matters more than the mean

If one worker experiences invalidation bursts while others do not, the result is not always lower average throughput. Often it is:

- slower request completion at P99
- coordination stalls for batches
- straggler-driven underutilization
- reduced effective cluster capacity

This is especially important when:

- requests are synchronized across workers
- batch completion waits on the slowest participant
- control-plane CPUs share cores with latency-sensitive runtimes

## Practical interpretation

The right question is usually not:

> Are TLB invalidations bad?

The better question is:

> Are translation invalidation bursts coinciding with the latency cliffs we already see?

That framing keeps the work grounded:

- not every invalidation burst is actionable
- not every tail spike is MMU-related
- but making the path observable closes a major attribution gap
