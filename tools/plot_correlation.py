#!/usr/bin/env python3
import argparse
import csv
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def parse_args():
    parser = argparse.ArgumentParser(description="Generate simple correlation plots")
    parser.add_argument("--input", required=True, help="correlation CSV")
    parser.add_argument("--output-dir", default="out/plots", help="plot output directory")
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


def collect_pairs(rows, left_key, right_key):
    pairs = []
    for row in rows:
        left_val = safe_float(row.get(left_key))
        right_val = safe_float(row.get(right_key))
        if left_val is None or right_val is None:
            continue
        pairs.append((left_val, right_val))
    return pairs


def write_plot(pairs, x_label, y_label, title, output_path):
    if not pairs:
        print(f"warning: skipping {os.path.basename(output_path)} due to missing columns or empty data")
        return
    xs = [pair[0] for pair in pairs]
    ys = [pair[1] for pair in pairs]
    plt.figure(figsize=(8, 5))
    plt.scatter(xs, ys, alpha=0.8)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=144)
    plt.close()


def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    rows = read_rows(args.input)

    write_plot(
        collect_pairs(rows, "tlb_invalidations_per_sec", "latency_p99_ms"),
        "TLB invalidations / sec",
        "P99 latency (ms)",
        "TLB invalidations vs P99 latency",
        os.path.join(args.output_dir, "tlb_invalidations_vs_p99.png"),
    )
    write_plot(
        collect_pairs(rows, "tlb_bytes_invalidated_per_sec", "latency_p99_ms"),
        "Bytes invalidated / sec",
        "P99 latency (ms)",
        "Bytes invalidated vs P99 latency",
        os.path.join(args.output_dir, "bytes_invalidated_vs_p99.png"),
    )
    write_plot(
        collect_pairs(rows, "gpu_utilization", "tlb_invalidations_per_sec"),
        "GPU utilization (%)",
        "TLB invalidations / sec",
        "GPU utilization vs TLB invalidations",
        os.path.join(args.output_dir, "gpu_util_vs_tlb_invalidations.png"),
    )

    scheduler_key = None
    for candidate in (
        "sched_cpu_runqueue_latency_ms",
        "sched_cpu_pressure_avg10",
        "sched_runnable_pressure",
    ):
        if any(safe_float(row.get(candidate)) is not None for row in rows):
            scheduler_key = candidate
            break
    if scheduler_key is not None:
        write_plot(
            collect_pairs(rows, scheduler_key, "tlb_invalidations_per_sec"),
            scheduler_key,
            "TLB invalidations / sec",
            "Scheduler pressure vs TLB invalidations",
            os.path.join(args.output_dir, "scheduler_pressure_vs_tlb_invalidations.png"),
        )
    else:
        print("warning: skipping scheduler plot due to missing scheduler columns")


if __name__ == "__main__":
    main()
