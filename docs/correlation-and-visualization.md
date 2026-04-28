# Correlation and Visualization

## Why timestamps matter

Invalidation counts alone are useful, but they do not say when the activity happened relative to user-visible symptoms. Time alignment is what turns a raw event stream into an investigation tool.

With timestamped 1 second buckets, the lab can compare:

- TLB invalidations per second
- bytes invalidated per second
- P99 latency
- GPU utilization and PCIe-side activity
- scheduler pressure and context-switch churn

That still does not prove causality. It only makes competing explanations easier to test.

## Correlation is not causation

This repository intentionally uses the word correlation unless the benchmark design isolates a causal path.

Examples:

- if invalidations rise just before P99 latency rises, that is a lead
- if GPU utilization dips during the same window, that is another lead
- if scheduler pressure is also elevated, that may be the confounder rather than the MMU path alone

The goal is to narrow the search space, not to overstate what a single trace can prove.

## How to interpret the signals

### P99 latency vs invalidation bursts

Look for repeated windows where invalidations per second or bytes invalidated per second increase before or during P99 latency spikes. The timing relationship matters more than any one raw count.

### GPU underutilization plus invalidation spikes

If GPU utilization dips while TLB invalidation activity rises, it can suggest that CPU-side translation or control-path work is interfering with feed paths, runtime coordination, or data movement. That is still a correlation, not automatic proof.

### Scheduler pressure as a confounder

High runqueue latency, context-switch churn, migration-like activity, or CPU pressure can create similar symptoms. If those signals move with invalidation bursts, the next step is controlled benchmarking rather than a causal conclusion.

## Commands

```bash
./run_experiment.sh
python3 tools/correlate_latency.py --tlb out/tlb_timeseries.csv --gpu out/gpu_timeseries.csv --sched out/sched_timeseries.csv
python3 tools/plot_correlation.py --input out/correlation.csv
```

To include latency data:

```bash
python3 tools/correlate_latency.py \
  --tlb out/tlb_timeseries.csv \
  --latency latency.csv \
  --gpu out/gpu_timeseries.csv \
  --sched out/sched_timeseries.csv \
  --output out/correlation.csv
```

## Practical workflow

1. Collect TLB, scheduler, and GPU samples during a benchmark or workload window.
2. Add latency data if your serving stack exposes it.
3. Generate `out/correlation.csv`.
4. Inspect the Pearson outputs and lagged correlation numbers.
5. Review the plots for repeated timing patterns.
6. Design a tighter benchmark if the signals look promising.
