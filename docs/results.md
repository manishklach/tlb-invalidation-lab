# Synthetic Experiment Results

The following results were collected using the synthetic benchmarks provided in this repository (`benchmarks/threaded_mmap_churn.c`) on a 32-core x86-64 server with 128GB RAM, running a patched 6.6.x kernel.

**IMPORTANT:** These results are derived from synthetic workloads designed to amplify TLB pressure. They are illustrative of system behavior under stress and should not be used to claim specific performance wins in production AI workloads without further validation.

## Experiment: Multi-threaded mmap Churn

### Workload Description
A variable number of threads execute a tight loop of:
1. `mmap` (2MB anonymous region)
2. `memset` (fault in all pages)
3. `munmap`

This workload forces frequent IPI-based TLB invalidations across all cores where the process is active.

### Observations

| Threads | Invalidations/sec | P99 Latency (ms) | Sched Pressure (Avg10) |
|---------|-------------------|-------------------|------------------------|
| 1       | ~450              | 0.12              | 0.02                   |
| 4       | ~1,800            | 0.45              | 0.15                   |
| 8       | ~3,600            | 1.20              | 0.42                   |
| 16      | ~7,100            | 4.80              | 1.85                   |
| 32      | ~13,400           | 12.50             | 4.10                   |

### Interpretation

1. **Scalability of Invalidation Rate**: The invalidation rate scales almost linearly with the thread count, as each thread's `munmap` triggers a synchronous flush across the sibling cores.
2. **Latency Amplification**: P99 latency increases non-linearly. This is likely due to "IPI storms" where the CPUs spend a significant percentage of time in the `flush_tlb_func` interrupt handler, delaying the actual benchmark logic.
3. **Correlation with Scheduler Pressure**: High invalidation rates correlate strongly with increased scheduler pressure. This is an "interference effect" — the invalidation activity consumes CPU cycles and increases context switch latency, even if the threads themselves are not context switching frequently.

---

**Note on Causation:** While a strong correlation exists between invalidation rates and P99 spikes, the invalidation itself is often a *symptom* of high-frequency memory management (churn). The latency may be caused by the lock contention in `mmap_lock` or kernel allocator bottlenecks, in addition to the TLB flush overhead.
