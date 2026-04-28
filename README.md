# tlb-invalidation-lab

**Observability and attribution for translation invalidation in AI infrastructure.**

Modern AI systems optimize compute and bandwidth, but often ignore how frequently they invalidate their own memory translations. `tlb-invalidation-lab` is a high-credibility research and debugging toolkit designed to make TLB invalidation observable, attributable, and measurable.

---

## 🎯 What this reveals

Translation invalidation is often a "hidden tax" on AI infrastructure. This toolkit reveals:

*   **Invalidation bursts preceding latency spikes**: Correlate MMU activity with P99 tail latency in distributed inference.
*   **GPU underutilization during MMU pressure**: Identify windows where host-side translation churn stalls GPU-to-host or host-to-GPU data movement.
*   **Scheduler contention**: See how TLB-related IPI storms amplify scheduler pressure and interrupt critical-path threads.

---

## 🚨 Constraints & Limitations

*   **Observability First**: This toolkit is designed for correlation and attribution. It does **not** claim causal performance improvements unless proven through controlled experiments.
*   **Research Patches**: The provided patches are lab artifacts. They are minimal, realistic, but intentionally not presented as upstream-ready.
*   **Instrumentation Requirement**: Full signal requires kernel instrumentation. While tools fallback gracefully, the most valuable insights come from the custom tracepoints.
*   **Correlation ≠ Causation**: The tools align signals in time, but they cannot prove causality.
*   **Architecture Variance**: Invalidation behavior and overhead vary significantly across CPU generations and architectures.

---

## What this repository provides

- research-grade kernel instrumentation sketches
- tracepoints for x86 TLB invalidation and MMU notifier activity
- an experimental procfs design sketch for `/proc/<pid>/tlb_stats`
- a sysfs capability view for broadcast invalidation-related CPU support
- educational x86-64 and arm64 architecture probe modules
- trace collection and parsing tools
- correlation, GPU, and scheduler sampling tools
- a lightweight health scoring tool
- a minimal Prometheus exporter
- simple matplotlib-based visualization scripts
- a one-command experiment runner
- synthetic benchmarks that drive invalidation-heavy VM behavior
- examples and CI for the userspace pieces

## Repository layout

```text
tlb-invalidation-lab/
├── README.md
├── LICENSE
├── docs/
├── arch-probes/
├── examples/
├── patches/
├── tools/
├── benchmarks/
├── vm/
├── visuals/
└── .github/workflows/
```

## Design principles

- observability over modification
- attribution over guesswork
- minimal kernel overhead
- realistic Linux 6.6+ assumptions
- no claims of direct GPU acceleration

## Recent Improvements

- timestamp-aware parsing with 1 second correlation buckets
- per-process Prometheus metrics with bounded label cardinality
- CPU-normalized health scoring based on per-core invalidation rate
- reduced arm64 trace-noise in the architecture sketch to avoid range-flooding
- a minimal QEMU bootstrap for lab validation work
- correlation tooling for latency, GPU, and scheduler signals
- a one-command experiment workflow

## Patch set overview

### `0001-x86-mm-add-tlb-invalidation-tracepoint.patch`

Adds an x86-oriented `tlb_invalidation` tracepoint around invalidation ranges. The event is designed to be cheap:

- numeric fields only
- `comm` captured through standard tracepoint helpers
- no ad hoc string formatting in the call site
- best-effort fanout and broadcast hints only when cheaply inferable

### `0002-mm-add-mmu-notifier-invalidation-tracepoint.patch`

Adds MMU notifier range tracepoints so users can correlate notifier-driven invalidation bursts with GPU UVM, RDMA, and related subsystems.

### `0003-proc-add-per-process-tlb-stats-sketch.patch`

Documents an explicitly experimental procfs sketch rather than pretending to provide an upstream-ready implementation. This is intentionally framed as secondary to tracepoint aggregation.

### `0004-x86-mm-expose-broadcast-invalidation-capability.patch`

Adds a small sysfs interface to expose whether the running system advertises hardware capability related to broadcast invalidation assistance. It does not implement new invalidation instructions and does not claim invention.

### `0005-x86-mm-add-arch-invalidation-probe-hooks.patch`

Sketches how x86 invalidation paths could expose architecture-flavored fields such as instruction family, local-versus-remote scope, and range size in pages.

### `0006-arm64-mm-add-arch-invalidation-probe-hooks.patch`

Sketches how arm64 TLBI paths could expose scope, range size, and barrier-phase context for observability.

## Quick start

### 1. Clone the repository

```bash
git clone https://github.com/manishklach/tlb-invalidation-lab.git
cd tlb-invalidation-lab
```

### 2. Inspect and apply patches

These patches are intended as lab artifacts. Review them against your target kernel tree before applying.

```bash
cd /path/to/linux
git apply /path/to/tlb-invalidation-lab/patches/0001-x86-mm-add-tlb-invalidation-tracepoint.patch
git apply /path/to/tlb-invalidation-lab/patches/0002-mm-add-mmu-notifier-invalidation-tracepoint.patch
git apply /path/to/tlb-invalidation-lab/patches/0004-x86-mm-expose-broadcast-invalidation-capability.patch

# 0003 is a design sketch, not a recommended default patch to apply.
# 0005 and 0006 are architecture-hook sketches, not upstream-ready patches.
```

Rebuild and boot the instrumented kernel using your standard workflow.

### 3. Build the synthetic benchmarks

```bash
cd /path/to/tlb-invalidation-lab/benchmarks
make
./run_bench.sh
```

### 4. Collect trace data

```bash
cd /path/to/tlb-invalidation-lab
sudo tools/collect_trace.sh 15
```

This writes trace output to:

```text
out/tlb_trace.txt
```

If the custom tracepoints are not present in the running kernel, the collector exits successfully, warns, and writes an empty capture file rather than failing hard.

### 5. Parse and aggregate the trace

```bash
python3 tools/parse_trace.py out/tlb_trace.txt --csv out/tlb_timeseries.csv
python3 tools/tlb_health_score.py out/tlb_timeseries.csv
```

The parser emits a time-series CSV with:

```text
timestamp,pid,comm,invalidations,bytes,invalidations_per_sec,bytes_invalidated_per_sec
```

If no matching events are present, the parser still emits a valid CSV header and warns on stderr.

### 6. Export metrics

```bash
python3 tools/prometheus_exporter.py --input out/tlb_timeseries.csv --listen 0.0.0.0 --port 9824 --max-process-labels 10
```

The exporter is designed to expose an error metric rather than crash if the input file is missing or malformed. It also emits top-N per-process labeled series and rolls the rest into `pid="other",comm="other"`.

### 7. Boot a minimal lab VM

```bash
cd /path/to/tlb-invalidation-lab/vm
./run_qemu.sh
```

See `vm/README.md` for bootstrap details and environment overrides.

## Correlation workflow

The repo can now align TLB invalidation activity with latency, GPU, and scheduler signals. That makes it possible to investigate timing relationships without claiming causation automatically.

One command:

```bash
./run_experiment.sh
```

Individual tools:

```bash
python3 tools/sample_gpu.py --duration 20 --output out/gpu_timeseries.csv
python3 tools/sample_sched.py --duration 20 --output out/sched_timeseries.csv
python3 tools/correlate_latency.py --tlb out/tlb_timeseries.csv --gpu out/gpu_timeseries.csv --sched out/sched_timeseries.csv --output out/correlation.csv
python3 tools/plot_correlation.py --input out/correlation.csv
```

If you have service latency data, add it with `--latency latency.csv`. The one-command runner does not synthesize a latency stream on its own.

Interpretation guidance:

- treat Pearson coefficients and plots as correlation, not proof of causation
- repeated timing patterns are more useful than a single noisy bucket
- scheduler pressure can confound apparent MMU effects
- GPU underutilization during high invalidation windows is a lead for further testing, not a verdict

## What this can reveal

- invalidation bursts preceding or overlapping P99 spikes
- GPU utilization dips during high invalidation windows
- scheduler pressure moving with invalidation spikes, which may point to a confounder
- per-process invalidation attribution showing which process names dominate noisy windows

## Architecture probe modules

The repository also includes small educational kernel-module probes under `arch-probes/` for x86-64 and arm64. These are intentionally minimal and are not substitutes for Linux MM code.

### x86-64

```bash
cd arch-probes/x86_64
make
sudo insmod tlb_probe_module.ko
dmesg | tail
sudo rmmod tlb_probe_module
```

### arm64

```bash
cd arch-probes/arm64
make
sudo insmod tlb_probe_module.ko
dmesg | tail
sudo rmmod tlb_probe_module
```

Use only on lab machines, VMs, or disposable test kernels.

## Example workflow

1. Run a baseline inference workload or synthetic churn benchmark.
2. Collect trace data for the same interval.
3. Aggregate invalidations by process and by source tracepoint.
4. Compare invalidation rate, bytes invalidated, and fanout against latency metrics.
5. Investigate high-rate notifier clients, mapping churn, and node-local stragglers.

For a small example, see:

- [examples/sample_trace.txt](examples/sample_trace.txt)
- [examples/sample_trace.csv](examples/sample_trace.csv)
- [examples/sample_trace_summary.txt](examples/sample_trace_summary.txt)
- [examples/sample_health_score.txt](examples/sample_health_score.txt)
- [examples/tlb_timeseries.csv](examples/tlb_timeseries.csv)
- [examples/latency_timeseries.csv](examples/latency_timeseries.csv)
- [examples/gpu_timeseries.csv](examples/gpu_timeseries.csv)
- [examples/sched_timeseries.csv](examples/sched_timeseries.csv)
- [examples/correlation.csv](examples/correlation.csv)

## Example Output

The files under `examples/` are synthetic documentation artifacts, not production captures.

`examples/sample_trace_summary.txt` summarizes a tiny capture with:

- one `tlb_invalidation` event
- two MMU notifier events
- 49,152 bytes invalidated
- average target CPU count of `8.00`

`examples/sample_health_score.txt` shows the corresponding health-score output for a 10 second observation window:

- `invalidations_per_sec_raw=0.10`
- `invalidations_per_sec_per_core=0.01`
- `bytes_invalidated_per_sec_raw=4915.20`
- `cpu_count=8`
- `health_class=green`

These examples are intentionally modest. They are meant to show the data shape and analysis flow, not to imply a dramatic performance issue.

For a longer synthetic walk-through, see `docs/results.md`.
For the aligned signal workflow specifically, see `docs/correlation-and-visualization.md`.

## What to look for

- invalidation bursts that line up with P99 latency spikes
- a single process causing disproportionate range churn
- MMU notifier activity clustered around GPU runtime events
- high fanout invalidations on CPUs that also handle networking or runtime threads
- sustained invalidation rates that do not show up in conventional GPU-centric dashboards

## Limitations

- the patches are intentionally observability-focused and are not upstream-ready
- tracepoints show correlation and attribution, not automatic root cause
- `target_cpu_count` is best-effort and architecture-context dependent
- broadcast invalidation detection is capability exposure, not behavioral proof
- the procfs sketch is documentation for an idea, not a claimed production implementation
- userland parsing assumes standard ftrace-style text output
- correlation tooling can align signals in time, but it cannot prove causality without controlled experiments
- GPU sampling depends on `nvidia-smi`; systems without NVIDIA GPUs will get an empty but valid GPU CSV

## Next Directions

Planned areas for future exploration and hardening:

* **eBPF Backport**: Develop an eBPF-based collector using `kprobes` on `native_flush_tlb_multi` for systems where kernel patching is not feasible.
* **NUMA Awareness**: Incorporate NUMA node IDs into trace outputs to identify if invalidation storms are localized to specific memory controllers or cross-socket fabrics.
* **Deeper Scheduler Correlation**: Better alignment between task migration events and invalidation bursts.
* **GPU Runtime Integration**: Direct visibility into UVM (Unified Virtual Memory) eviction events.
* **Adaptive Alerting**: Thresholds that adjust based on workload class (e.g., training vs. low-latency inference).

## Audience

This repository is for:

- Linux kernel engineers
- AI infrastructure performance teams
- systems researchers studying hidden latency sources
- platform teams investigating cluster stragglers

If your current observability stack ends at CPU utilization, GPU utilization, and network counters, this lab is meant to help fill in one of the missing layers between them.
