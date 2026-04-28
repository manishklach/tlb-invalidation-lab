#!/usr/bin/env python3
import argparse
import csv
import os
import time


HEADERS = [
    "timestamp",
    "cpu_runqueue_latency_ms",
    "context_switches",
    "cpu_migrations",
    "cpu_pressure_avg10",
    "cpu_pressure_avg60",
    "runnable_pressure",
]


def parse_args():
    parser = argparse.ArgumentParser(description="Best-effort scheduler signal sampler")
    parser.add_argument("--interval", type=float, default=1.0, help="sampling interval in seconds")
    parser.add_argument("--duration", type=float, default=10.0, help="sampling duration in seconds")
    parser.add_argument("--output", default="out/sched_timeseries.csv", help="output CSV path")
    return parser.parse_args()


def read_proc_stat():
    data = {}
    with open("/proc/stat", "r", encoding="utf-8") as handle:
        for line in handle:
            parts = line.split()
            if len(parts) < 2:
                continue
            if parts[0] in ("ctxt", "procs_running"):
                data[parts[0]] = int(parts[1])
    return data


def read_pressure():
    result = {"cpu_pressure_avg10": None, "cpu_pressure_avg60": None, "runnable_pressure": None}
    try:
        with open("/proc/pressure/cpu", "r", encoding="utf-8") as handle:
            for line in handle:
                parts = line.split()
                if not parts:
                    continue
                name = parts[0]
                metrics = {}
                for item in parts[1:]:
                    if "=" not in item:
                        continue
                    key, value = item.split("=", 1)
                    metrics[key] = float(value)
                if name == "some":
                    result["cpu_pressure_avg10"] = metrics.get("avg10")
                    result["cpu_pressure_avg60"] = metrics.get("avg60")
                    result["runnable_pressure"] = metrics.get("avg10")
    except OSError:
        pass
    return result


def read_schedstat():
    result = {"wait_ns": 0, "timeslices": 0, "migration_proxy": 0}
    try:
        with open("/proc/schedstat", "r", encoding="utf-8") as handle:
            for line in handle:
                parts = line.split()
                if not parts:
                    continue
                if parts[0].startswith("cpu") and parts[0][3:].isdigit() and len(parts) >= 10:
                    result["wait_ns"] += int(parts[8])
                    result["timeslices"] += int(parts[9])
                elif parts[0].startswith("domain") and len(parts) >= 4:
                    try:
                        result["migration_proxy"] += int(parts[-2])
                    except ValueError:
                        continue
    except OSError:
        pass
    return result


def sample_once():
    data = {}
    data.update(read_proc_stat())
    data.update(read_pressure())
    data.update(read_schedstat())
    return data


def main():
    args = parse_args()
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    with open(args.output, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        writer.writeheader()

        if not os.path.exists("/proc/stat"):
            print("warning: /proc/stat not found; writing empty scheduler CSV")
            return

        previous = sample_once()
        start = time.time()

        while True:
            time.sleep(args.interval)
            now = time.time()
            current = sample_once()
            elapsed = max(now - start, args.interval)
            delta_context = float(current.get("ctxt", 0) - previous.get("ctxt", 0)) / args.interval
            delta_migrations = float(current.get("migration_proxy", 0) - previous.get("migration_proxy", 0)) / args.interval
            wait_delta = current.get("wait_ns", 0) - previous.get("wait_ns", 0)
            timeslice_delta = current.get("timeslices", 0) - previous.get("timeslices", 0)
            if timeslice_delta > 0:
                runqueue_ms = (wait_delta / timeslice_delta) / 1_000_000.0
            else:
                runqueue_ms = 0.0

            writer.writerow({
                "timestamp": int(now),
                "cpu_runqueue_latency_ms": f"{runqueue_ms:.2f}",
                "context_switches": f"{delta_context:.2f}",
                "cpu_migrations": f"{delta_migrations:.2f}",
                "cpu_pressure_avg10": "" if current.get("cpu_pressure_avg10") is None else f"{current['cpu_pressure_avg10']:.2f}",
                "cpu_pressure_avg60": "" if current.get("cpu_pressure_avg60") is None else f"{current['cpu_pressure_avg60']:.2f}",
                "runnable_pressure": "" if current.get("runnable_pressure") is None else f"{current['runnable_pressure']:.2f}",
            })
            handle.flush()
            previous = current
            if now - start >= args.duration:
                break


if __name__ == "__main__":
    main()
