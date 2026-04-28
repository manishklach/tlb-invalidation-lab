# End-to-End Example Walkthrough

This guide shows you how to use the `tlb-invalidation-lab` toolkit to identify a TLB invalidation burst and correlate it with application latency.

## Prerequisites
- A Linux system with the kernel patches from `patches/` applied.
- `python3` and `matplotlib` installed.
- Root or sudo access (to enable ftrace).

---

## Step 1: Run the Benchmark
Launch the threaded mmap churn benchmark to generate a controlled "invalidation storm."

```bash
# Compile the benchmarks
cd benchmarks && make

# Run 16 threads for 30 seconds
./threaded_mmap_churn 16 100000 1048576 &
BENCH_PID=$!
```

## Step 2: Collect the Trace
While the benchmark is running, collect the kernel trace.

```bash
# Move to the tools directory
cd ../tools

# Collect 10 seconds of trace data
sudo ./collect_trace.sh 10
```
This produces `out/tlb_trace.txt`.

## Step 3: Parse the Trace
Convert the raw ftrace text into a structured CSV for analysis.

```bash
python3 parse_trace.py out/tlb_trace.txt --csv out/tlb_trace.csv
```
This aggregates events into 1-second buckets and attributes them to the benchmark PID.

## Step 4: Run Correlation Analysis
Generate a unified correlation CSV by combining the TLB data with scheduler and latency telemetry.

```bash
# In a real scenario, you would have separate latency/scheduler logs.
# For this example, we'll use the provided dummy aggregator.
python3 correlate_latency.py --tlb out/tlb_trace.csv --output out/correlation.csv
```

## Step 5: Generate Visualizations
Create plots to see the relationship between invalidations and latency.

```bash
python3 plot_correlation.py --input out/correlation.csv --output-dir out/plots
```

## Step 6: Verify the Output
Open `out/plots/tlb_invalidations_vs_p99.png`. You should see a clear (likely non-linear) upward trend indicating that as invalidation frequency increased, the benchmark's measured latency also increased.

**Next Step**: Refer to [docs/interpretation-guide.md](interpretation-guide.md) to decide if the observed rate is concerning for your specific architecture.
