#!/usr/bin/env python3
import argparse
import csv
import os
import shutil
import subprocess
import sys
import time


GPU_HEADERS = [
    "timestamp",
    "gpu_id",
    "gpu_uuid",
    "utilization",
    "mem_utilization",
    "pcie_tx_mb_s",
    "pcie_rx_mb_s",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Sample GPU utilization using nvidia-smi")
    parser.add_argument("--interval", type=float, default=1.0, help="sampling interval in seconds")
    parser.add_argument("--duration", type=float, default=10.0, help="sampling duration in seconds")
    parser.add_argument("--output", default="out/gpu_timeseries.csv", help="output CSV path")
    return parser.parse_args()


def write_empty_csv(path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(GPU_HEADERS)


def query_gpu_rows():
    command = [
        "nvidia-smi",
        "--query-gpu=index,uuid,utilization.gpu,utilization.memory",
        "--format=csv,noheader,nounits",
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    rows = []
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 4:
            continue
        rows.append({
            "gpu_id": parts[0],
            "gpu_uuid": parts[1],
            "utilization": parts[2],
            "mem_utilization": parts[3],
            "pcie_tx_mb_s": "",
            "pcie_rx_mb_s": "",
        })
    return rows


def try_query_pcie():
    command = ["nvidia-smi", "dmon", "-s", "t", "-c", "1"]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    metrics = {}
    for line in result.stdout.splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            gpu_id = parts[0]
            rx_val = parts[-2]
            tx_val = parts[-1]
            float(rx_val)
            float(tx_val)
        except ValueError:
            continue
        metrics[gpu_id] = {
            "pcie_rx_mb_s": rx_val,
            "pcie_tx_mb_s": tx_val,
        }
    return metrics


def main():
    args = parse_args()
    if shutil.which("nvidia-smi") is None:
        print("warning: nvidia-smi not found; writing empty GPU CSV", file=sys.stderr)
        write_empty_csv(args.output)
        return

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    start = time.time()

    with open(args.output, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=GPU_HEADERS)
        writer.writeheader()

        while True:
            now = time.time()
            if now - start >= args.duration:
                break
            timestamp = int(now)
            try:
                rows = query_gpu_rows()
                try:
                    pcie_metrics = try_query_pcie()
                except subprocess.SubprocessError:
                    pcie_metrics = {}
                for row in rows:
                    pcie_row = pcie_metrics.get(row["gpu_id"], {})
                    row["timestamp"] = timestamp
                    row["pcie_tx_mb_s"] = pcie_row.get("pcie_tx_mb_s", row["pcie_tx_mb_s"])
                    row["pcie_rx_mb_s"] = pcie_row.get("pcie_rx_mb_s", row["pcie_rx_mb_s"])
                    writer.writerow(row)
                handle.flush()
            except subprocess.SubprocessError as exc:
                print(f"warning: GPU sampling failed: {exc}", file=sys.stderr)
                break
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
