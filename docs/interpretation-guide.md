# TLB Invalidation Interpretation Guide

This guide helps you reason about the metrics collected by `tlb-invalidation-lab`.

## 1. What is a "High" Invalidation Rate?

There is no universal "bad" number. TLB invalidation cost is highly dependent on:
- **Core Count**: The IPI (Inter-Processor Interrupt) cost scales with the number of CPUs the process is active on.
- **Microarchitecture**: Newer CPUs (e.g., AMD with `INVLPGB` or ARM64 with broadcast TLBI) handle invalidations much more efficiently than legacy IPI paths.
- **Workload Phase**: A high rate during a "KV Cache Cleanup" phase may be expected, while a high rate during steady-state "Token Generation" may indicate a regression.

### Baseline Heuristics (for 32-64 core systems)
- **Low (< 100/sec)**: Standard system background noise. Negligible impact.
- **Moderate (100 - 1,000/sec)**: Common in memory-intensive AI applications. May cause measurable but small latency jitters.
- **High (1,000 - 10,000/sec)**: Potential "Invalidation Storm". Likely causing 1–5% overhead in compute efficiency.
- **Extreme (> 10,000/sec)**: Pathological churn. Likely consuming 10%+ of system throughput in IPI overhead and pipeline stalls.

## 2. Distinguishing Causes

### Allocator Churn
- **Pattern**: High `mmap`/`munmap` frequency in trace.
- **TLB Effect**: Frequent synchronous invalidations across all active cores.
- **Symptom**: Strong correlation between `tlb_invalidations_per_sec` and `mmap_lock` contention (if measured).

### GPU / UVM Effects
- **Pattern**: `mmu_notifier` events correlated with GPU kernel launches or results.
- **TLB Effect**: GPU drivers often use MMU notifiers to stay in sync with system memory. If the GPU is frequently "demoting" pages or handling page faults, it will trigger system-wide invalidations.
- **Symptom**: Bursts of invalidations preceding GPU under-utilization periods.

### Scheduler Artifacts
- **Pattern**: High scheduler pressure accompanying moderate invalidation rates.
- **Effect**: If the scheduler is migrating threads frequently across NUMA nodes, the kernel may need to flush TLBs to maintain consistency.
- **Symptom**: `tlb_invalidations` correlate with `sched_migrate_task` trace events.

## 3. Correlation vs. Causation

The tools in this repository show **correlation**.
- **The "Symptom" Case**: High invalidation is often just a symptom of the application doing "too much work" (e.g., freeing too many small objects). The latency comes from the work itself, not just the TLB flush.
- **The "Amplifier" Case**: The TLB flush acts as a multiplier. For every 1 microsecond of "real" work, the IPI storm adds 0.5 microseconds of "wait for others to flush" time. This is where this lab's data is most useful for performance engineers.

## 4. Normalization

When comparing across different hardware, use **Normalized Invalidation Cost**:
`Cost = (Invalidations / sec) * (Active CPU Count)`
A 100/sec rate on 128 cores can be more disruptive than a 1000/sec rate on 4 cores.
