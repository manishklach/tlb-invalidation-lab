#!/usr/bin/env python3
import argparse
import csv
import math
import os
from collections import defaultdict


def parse_args():
    parser = argparse.ArgumentParser(
        description="Correlate TLB invalidation activity with latency, GPU, and scheduler signals"
    )
    parser.add_argument("--tlb", required=True, help="TLB time-series CSV from parse_trace.py")
    parser.add_argument("--latency", help="optional latency CSV")
    parser.add_argument("--gpu", help="optional GPU CSV")
    parser.add_argument("--sched", help="optional scheduler CSV")
    parser.add_argument("--output", default="out/correlation.csv", help="merged output CSV")
    return parser.parse_args()


def safe_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def read_csv_rows(path):
    if not path:
        return []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))
    except OSError as exc:
        print(f"warning: unable to read {path}: {exc}")
        return []


def load_tlb(rows):
    totals = defaultdict(lambda: {
        "tlb_invalidations_per_sec": 0.0,
        "tlb_bytes_invalidated_per_sec": 0.0,
    })
    per_process = defaultdict(lambda: defaultdict(float))

    for row in rows:
        ts = row.get("timestamp")
        comm = row.get("comm", "")
        invalidations = safe_float(row.get("invalidations_per_sec")) or 0.0
        bytes_invalidated = safe_float(row.get("bytes_invalidated_per_sec")) or 0.0
        if ts is None or ts == "":
            continue
        totals[ts]["tlb_invalidations_per_sec"] += invalidations
        totals[ts]["tlb_bytes_invalidated_per_sec"] += bytes_invalidated
        if comm:
            per_process[comm][ts] += invalidations

    return totals, per_process


def load_latency(rows):
    data = {}
    for row in rows:
        ts = row.get("timestamp")
        if ts is None or ts == "":
            continue
        data[ts] = {
            "latency_p50_ms": safe_float(row.get("p50_ms")),
            "latency_p95_ms": safe_float(row.get("p95_ms")),
            "latency_p99_ms": safe_float(row.get("p99_ms")),
        }
    return data


def load_gpu(rows):
    buckets = defaultdict(lambda: {
        "count": 0.0,
        "gpu_utilization": 0.0,
        "gpu_mem_utilization": 0.0,
        "gpu_pcie_tx_mb_s": 0.0,
        "gpu_pcie_rx_mb_s": 0.0,
    })

    for row in rows:
        ts = row.get("timestamp")
        if ts is None or ts == "":
            continue
        buckets[ts]["count"] += 1.0
        buckets[ts]["gpu_utilization"] += safe_float(row.get("utilization")) or 0.0
        buckets[ts]["gpu_mem_utilization"] += safe_float(row.get("mem_utilization")) or 0.0
        buckets[ts]["gpu_pcie_tx_mb_s"] += safe_float(row.get("pcie_tx_mb_s")) or 0.0
        buckets[ts]["gpu_pcie_rx_mb_s"] += safe_float(row.get("pcie_rx_mb_s")) or 0.0

    data = {}
    for ts, bucket in buckets.items():
        count = bucket["count"] or 1.0
        data[ts] = {
            "gpu_utilization": bucket["gpu_utilization"] / count,
            "gpu_mem_utilization": bucket["gpu_mem_utilization"] / count,
            "gpu_pcie_tx_mb_s": bucket["gpu_pcie_tx_mb_s"],
            "gpu_pcie_rx_mb_s": bucket["gpu_pcie_rx_mb_s"],
        }
    return data


def load_sched(rows):
    data = {}
    for row in rows:
        ts = row.get("timestamp")
        if ts is None or ts == "":
            continue
        data[ts] = {
            "sched_cpu_runqueue_latency_ms": safe_float(row.get("cpu_runqueue_latency_ms")),
            "sched_context_switches": safe_float(row.get("context_switches")),
            "sched_cpu_migrations": safe_float(row.get("cpu_migrations")),
            "sched_cpu_pressure_avg10": safe_float(row.get("cpu_pressure_avg10")),
            "sched_cpu_pressure_avg60": safe_float(row.get("cpu_pressure_avg60")),
            "sched_runnable_pressure": safe_float(row.get("runnable_pressure")),
        }
    return data


def pearson(xs, ys):
    if len(xs) < 2 or len(ys) < 2 or len(xs) != len(ys):
        return None
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    num = 0.0
    den_x = 0.0
    den_y = 0.0
    for x_val, y_val in zip(xs, ys):
        dx = x_val - mean_x
        dy = y_val - mean_y
        num += dx * dy
        den_x += dx * dx
        den_y += dy * dy
    if den_x <= 0.0 or den_y <= 0.0:
        return None
    return num / math.sqrt(den_x * den_y)


def series_correlation(rows, left_key, right_key, lag_seconds=0):
    xs = []
    ys = []
    by_timestamp = {int(row["timestamp"]): row for row in rows}
    for ts, row in sorted(by_timestamp.items()):
        other = by_timestamp.get(ts + lag_seconds)
        if other is None:
            continue
        left_val = safe_float(row.get(left_key))
        right_val = safe_float(other.get(right_key))
        if left_val is None or right_val is None:
            continue
        xs.append(left_val)
        ys.append(right_val)
    return pearson(xs, ys)


def top_correlated_processes(rows, per_process):
    by_ts_p99 = {
        int(row["timestamp"]): safe_float(row.get("latency_p99_ms"))
        for row in rows
        if row.get("timestamp") not in (None, "")
    }
    scores = []
    for comm, ts_map in per_process.items():
        xs = []
        ys = []
        for ts, invalidations in sorted(ts_map.items(), key=lambda item: int(item[0])):
            p99 = by_ts_p99.get(int(ts))
            if p99 is None:
                continue
            xs.append(invalidations)
            ys.append(p99)
        corr = pearson(xs, ys)
        if corr is not None:
            scores.append((abs(corr), corr, comm))
    scores.sort(reverse=True)
    return scores[:5]


def main():
    args = parse_args()
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    tlb_totals, per_process = load_tlb(read_csv_rows(args.tlb))
    latency = load_latency(read_csv_rows(args.latency))
    gpu = load_gpu(read_csv_rows(args.gpu))
    sched = load_sched(read_csv_rows(args.sched))

    timestamps = sorted({
        *tlb_totals.keys(),
        *latency.keys(),
        *gpu.keys(),
        *sched.keys(),
    }, key=lambda value: int(value))

    rows = []
    for ts in timestamps:
        row = {
            "timestamp": ts,
            "tlb_invalidations_per_sec": "",
            "tlb_bytes_invalidated_per_sec": "",
            "latency_p50_ms": "",
            "latency_p95_ms": "",
            "latency_p99_ms": "",
            "gpu_utilization": "",
            "gpu_mem_utilization": "",
            "gpu_pcie_tx_mb_s": "",
            "gpu_pcie_rx_mb_s": "",
            "sched_cpu_runqueue_latency_ms": "",
            "sched_context_switches": "",
            "sched_cpu_migrations": "",
            "sched_cpu_pressure_avg10": "",
            "sched_cpu_pressure_avg60": "",
            "sched_runnable_pressure": "",
        }
        if ts in tlb_totals:
            row["tlb_invalidations_per_sec"] = f"{tlb_totals[ts]['tlb_invalidations_per_sec']:.2f}"
            row["tlb_bytes_invalidated_per_sec"] = f"{tlb_totals[ts]['tlb_bytes_invalidated_per_sec']:.2f}"
        if ts in latency:
            for key, value in latency[ts].items():
                row[key] = "" if value is None else f"{value:.2f}"
        if ts in gpu:
            for key, value in gpu[ts].items():
                row[key] = "" if value is None else f"{value:.2f}"
        if ts in sched:
            for key, value in sched[ts].items():
                row[key] = "" if value is None else f"{value:.2f}"
        rows.append(row)

    fieldnames = list(rows[0].keys()) if rows else [
        "timestamp",
        "tlb_invalidations_per_sec",
        "tlb_bytes_invalidated_per_sec",
        "latency_p50_ms",
        "latency_p95_ms",
        "latency_p99_ms",
        "gpu_utilization",
        "gpu_mem_utilization",
        "gpu_pcie_tx_mb_s",
        "gpu_pcie_rx_mb_s",
        "sched_cpu_runqueue_latency_ms",
        "sched_context_switches",
        "sched_cpu_migrations",
        "sched_cpu_pressure_avg10",
        "sched_cpu_pressure_avg60",
        "sched_runnable_pressure",
    ]

    with open(args.output, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    if any(row.get("latency_p99_ms") not in ("", None) for row in rows):
        corr_inv = series_correlation(rows, "tlb_invalidations_per_sec", "latency_p99_ms", 0)
        corr_bytes = series_correlation(rows, "tlb_bytes_invalidated_per_sec", "latency_p99_ms", 0)
        print(f"pearson_invalidations_vs_p99={corr_inv if corr_inv is not None else 'n/a'}")
        print(f"pearson_bytes_vs_p99={corr_bytes if corr_bytes is not None else 'n/a'}")
        for lag in (1, 5, 10):
            lag_inv = series_correlation(rows, "tlb_invalidations_per_sec", "latency_p99_ms", lag)
            lag_bytes = series_correlation(rows, "tlb_bytes_invalidated_per_sec", "latency_p99_ms", lag)
            print(f"pearson_invalidations_vs_p99_lag_{lag}s={lag_inv if lag_inv is not None else 'n/a'}")
            print(f"pearson_bytes_vs_p99_lag_{lag}s={lag_bytes if lag_bytes is not None else 'n/a'}")
        for _, corr, comm in top_correlated_processes(rows, per_process):
            print(f"top_correlated_process={comm},pearson={corr}")
    else:
        print("warning: latency_p99_ms column unavailable; correlation outputs skipped")


if __name__ == "__main__":
    main()
