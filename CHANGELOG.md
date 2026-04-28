# Changelog

## [0.1.0] — 2026-04-28

### Added
- **Kernel Instrumentation (Patch Set)**: Research-grade tracepoints for TLB invalidation (x86) and MMU notifier activity.
- **Architecture Probe Modules**: Educational modules for x86-64 (`invlpg`) and arm64 (`TLBI`) instructions.
- **Correlation Pipeline**: Tools for time-aligned analysis of TLB traces, latency metrics, and GPU utilization.
- **Health Scoring**: Normalized metrics for invalidations per second per core with green/yellow/red thresholds.
- **Visualization**: Matplotlib-based plotting for burst correlation and scheduler pressure analysis.
- **Benchmarks**: `mmap_churn`, `mprotect_churn`, and `threaded_mmap_churn` synthetic workloads.
- **QEMU Bootstrap**: Lightweight kernel boot environment for instrumentation testing.
- **Examples**: Synthetic trace summaries and health scores for quick tool validation.

### Capabilities
- Attribution of invalidation activity to specific PIDs.
- Correlation of translation churn with P99 latency and GPU stalls.
- Measurement of broadcast invalidation fanout.

### Roadmap
- **eBPF Backport**: Non-invasive collection via `kprobes`. 
- **NUMA Awareness**: Per-socket/per-controller invalidation attribution. 
- **GPU UVM Integration**: Correlating MMU notifiers with GPU-side page faults.
