#!/usr/bin/env python3
import argparse
import csv
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def parse_args():
    parser = argparse.ArgumentParser(description="Generate upgraded correlation plots")
    parser.add_argument("--input", required=True, help="correlation CSV")
    parser.add_argument("--output-dir", default="out/plots", help="plot output directory")
    parser.add_argument("--window", type=int, default=5, help="smoothing window size")
    return parser.parse_args()


def safe_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def read_rows(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
    except OSError as exc:
        print(f"warning: unable to read {path}: {exc}")
        return []


def moving_average(data, window):
    if len(data) < window:
        return data
    ret = []
    for i in range(len(data)):
        start = max(0, i - window // 2)
        end = min(len(data), i + window // 2 + 1)
        chunk = data[start:end]
        ret.append(sum(chunk) / len(chunk))
    return ret


def write_correlation_plot(rows, x_key, y_key, x_label, y_label, title_base, output_path, window):
    # Collect shared data points
    points = []
    for row in rows:
        x_val = safe_float(row.get(x_key))
        y_val = safe_float(row.get(y_key))
        if x_val is not None and y_val is not None:
            points.append((x_val, y_val))
    
    if not points:
        print(f"warning: skipping {os.path.basename(output_path)} due to missing data")
        return

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    plt.figure(figsize=(10, 6))
    
    # Raw scatter
    plt.scatter(xs, ys, alpha=0.3, s=10, label="Raw data", color="#3498db")
    
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(f"{title_base}\n(Observed correlation, not proven causation)")
    plt.grid(True, alpha=0.2)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=144)
    plt.close()


def write_timeseries_plot(rows, y1_key, y2_key, y1_label, y2_label, title_base, output_path, window):
    ts = [safe_float(r.get("timestamp")) for r in rows]
    v1 = [safe_float(r.get(y1_key)) for r in rows]
    v2 = [safe_float(r.get(y2_key)) for r in rows]
    
    # Filter for points where all three exist
    data = [(t, a, b) for t, a, b in zip(ts, v1, v2) if t is not None and a is not None and b is not None]
    if not data:
        return
    
    data.sort() # Ensure time order
    ts = [d[0] for d in data]
    v1 = [d[1] for d in data]
    v2 = [d[2] for d in data]
    
    v1_smooth = moving_average(v1, window)
    v2_smooth = moving_average(v2, window)
    
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    color1 = "#e74c3c"
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel(y1_label, color=color1)
    ax1.plot(ts, v1, alpha=0.15, color=color1)
    ax1.plot(ts, v1_smooth, color=color1, linewidth=2, label=f"{y1_label} (smoothed)")
    ax1.tick_params(axis='y', labelcolor=color1)
    
    ax2 = ax1.twinx()
    color2 = "#2ecc71"
    ax2.set_ylabel(y2_label, color=color2)
    ax2.plot(ts, v2, alpha=0.15, color=color2)
    ax2.plot(ts, v2_smooth, color=color2, linewidth=2, label=f"{y2_label} (smoothed)")
    ax2.tick_params(axis='y', labelcolor=color2)
    
    plt.title(f"{title_base} over Time\n(Time alignment for correlation analysis)")
    fig.tight_layout()
    plt.savefig(output_path, dpi=144)
    plt.close()


def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    rows = read_rows(args.input)
    if not rows:
        return

    # 1. Legacy Correlation plots (filenames expected by CI)
    write_correlation_plot(rows, "tlb_invalidations_per_sec", "latency_p99_ms",
                           "TLB invalidations / sec", "P99 latency (ms)",
                           "TLB invalidations vs P99 latency",
                           os.path.join(args.output_dir, "tlb_invalidations_vs_p99.png"), args.window)
    
    write_correlation_plot(rows, "tlb_bytes_invalidated_per_sec", "latency_p99_ms",
                           "Bytes invalidated / sec", "P99 latency (ms)",
                           "Bytes invalidated vs P99 latency",
                           os.path.join(args.output_dir, "bytes_invalidated_vs_p99.png"), args.window)

    write_correlation_plot(rows, "gpu_utilization", "tlb_invalidations_per_sec",
                           "GPU utilization (%)", "TLB invalidations / sec",
                           "GPU utilization vs TLB invalidations",
                           os.path.join(args.output_dir, "gpu_util_vs_tlb_invalidations.png"), args.window)

    # Scheduler plot (if columns exist)
    scheduler_key = None
    for candidate in ("sched_cpu_runqueue_latency_ms", "sched_cpu_pressure_avg10", "sched_runnable_pressure"):
        if any(safe_float(row.get(candidate)) is not None for row in rows):
            scheduler_key = candidate
            break
    
    if scheduler_key:
        write_correlation_plot(rows, scheduler_key, "tlb_invalidations_per_sec",
                               scheduler_key, "TLB invalidations / sec",
                               "Scheduler pressure vs TLB invalidations",
                               os.path.join(args.output_dir, "scheduler_pressure_vs_tlb_invalidations.png"), args.window)

    # 2. New Upgraded Time-series plots (Time alignment + Smoothing)
    write_timeseries_plot(rows, "tlb_invalidations_per_sec", "latency_p99_ms",
                          "TLB invalidations / sec", "P99 latency (ms)",
                          "TLB Activity vs Latency",
                          os.path.join(args.output_dir, "ts_tlb_vs_latency.png"), args.window)
    
    write_timeseries_plot(rows, "tlb_invalidations_per_sec", "gpu_utilization",
                          "TLB invalidations / sec", "GPU Utilization (%)",
                          "TLB Activity vs GPU Utilization",
                          os.path.join(args.output_dir, "ts_tlb_vs_gpu.png"), args.window)

    print(f"Upgraded plots generated in {args.output_dir}")


if __name__ == "__main__":
    main()
