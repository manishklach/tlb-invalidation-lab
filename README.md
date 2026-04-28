# tlb-invalidation-lab

Making TLB invalidation observable, attributable, and measurable in modern AI workloads.

`tlb-invalidation-lab` is an observability and attribution lab for a part of Linux performance that is often felt before it is seen: translation invalidation activity.

AI inference stacks are often described as GPU-bound. That description is directionally true, but incomplete. Modern inference nodes also depend on CPU-side memory-management paths for pinned memory, GPU UVM interactions, RDMA buffers, allocator churn, memory-mapped state, and process lifecycle noise. When those paths trigger TLB invalidations, remote shootdowns and page-table synchronization can interrupt CPU progress, perturb scheduling, and widen tail latency.

This repository does not claim a magic fix. It does not rewrite the kernel, replace the MM subsystem, or promise direct GPU acceleration.

It does provide a practical way to answer a harder and more useful question:

> The GPU is not always slow because the GPU is slow.  
> Sometimes the memory translation subsystem is disrupting execution.

## Status

This repository is a research and debugging lab patch set. It is intended to help engineers inspect translation invalidation behavior, prototype instrumentation ideas, and correlate MMU activity with latency symptoms.

It is not upstream-ready production kernel code, and it should not be read as a claim that the included patches are suitable for broad deployment without kernel-version-specific review and validation.

## Safety

Test these patches only on non-production kernels, development hosts, or disposable VMs first.

- do not apply the patch set directly to production kernels without review
- treat the procfs sketch as experimental design material, not a production interface
- validate tracepoint overhead and behavior in your own kernel tree before relying on the results

## Why this matters

In large inference systems, the visible symptom is often simple:

- tokens arrive late
- one worker becomes a straggler
- batch completion spreads out
- P99 latency grows while averages still look acceptable

The hidden cause can be less obvious. TLB invalidation bursts can force CPUs to stop useful work, service IPIs, synchronize address-space updates, and re-establish translation state. On nodes that also manage networking, storage, orchestration, and GPU runtime control paths, those interruptions can show up as jitter rather than an obvious fault.

That matters because modern AI jobs amplify outliers.

### Tail latency and the straggler effect

P99 latency is the latency seen by the slowest 1 percent of requests or operations. In distributed inference, that tail matters disproportionately:

- one noisy node can delay a coordinated batch
- one control-plane CPU can become the pacing item for a GPU server
- one worker with repeated invalidation bursts can stretch end-to-end completion time

In other words, even when average throughput looks stable, invalidation-driven CPU disruption can still lower effective cluster capacity.

## Why AI workloads can trigger MMU activity

The repo focuses on patterns that commonly appear in modern inference and adjacent infrastructure:

- pinned host memory used for DMA and staging paths
- GPU UVM migrations and notifier-driven invalidation coordination
- RDMA buffer registration and teardown
- `mmap()` / `munmap()` churn from short-lived mappings
- memory-mapped model artifacts or KV-cache-adjacent state
- allocator pressure that repeatedly changes protections or virtual layout

These are not bugs by themselves. They are normal systems behaviors. The goal here is to make their invalidation side effects visible enough to correlate with user-visible performance.

## Hardware nuance

This repo also sits inside a broader systems thesis: hidden infrastructure variables often degrade effective compute without looking like compute failures.

- PCIe errors can degrade data movement and trigger fallback or downtraining
- TLB invalidation activity can degrade address-translation continuity and interrupt CPU execution

On modern platforms, especially those pushing PCIe Gen5 margins, signal-integrity sensitivity and link instability can already make throughput less deterministic than nominal specs suggest. Translation disruption is a different mechanism, but it belongs in the same category of hidden capacity loss: the machine is present, powered on, and seemingly healthy, yet useful work arrives later than expected.

## What this repository provides

- research-grade kernel instrumentation sketches
- tracepoints for x86 TLB invalidation and MMU notifier activity
- an experimental procfs design sketch for `/proc/<pid>/tlb_stats`
- a sysfs capability view for broadcast invalidation-related CPU support
- educational x86-64 and arm64 architecture probe modules
- trace collection and parsing tools
- a lightweight health scoring tool
- a minimal Prometheus exporter
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
├── visuals/
└── .github/workflows/
```

## Design principles

- observability over modification
- attribution over guesswork
- minimal kernel overhead
- realistic Linux 6.6+ assumptions
- no claims of direct GPU acceleration

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
python3 tools/parse_trace.py out/tlb_trace.txt --csv out/tlb_trace.csv
python3 tools/tlb_health_score.py out/tlb_trace.csv
```

If no matching events are present, the parser still emits a valid CSV header and warns on stderr.

### 6. Export metrics

```bash
python3 tools/prometheus_exporter.py --input out/tlb_trace.csv --listen 0.0.0.0 --port 9824
```

The exporter is designed to expose an error metric rather than crash if the input file is missing or malformed.

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

## Audience

This repository is for:

- Linux kernel engineers
- AI infrastructure performance teams
- systems researchers studying hidden latency sources
- platform teams investigating cluster stragglers

If your current observability stack ends at CPU utilization, GPU utilization, and network counters, this lab is meant to help fill in one of the missing layers between them.
