#!/usr/bin/env python3
import argparse
import csv
import os
import sys


def parse_args():
    parser = argparse.ArgumentParser(description="Compute a simple TLB health score")
    parser.add_argument("csv_file", help="time-series CSV from parse_trace.py")
    parser.add_argument("--window-seconds", type=float, default=10.0,
                        help="observation window in seconds")
    return parser.parse_args()


def classify_per_core(invalidations_per_sec_per_core):
    if invalidations_per_sec_per_core < 5.0:
        return "green"
    if invalidations_per_sec_per_core <= 20.0:
        return "yellow"
    return "red"


def score_from_class(health_class):
    if health_class == "green":
        return 20.0
    if health_class == "yellow":
        return 60.0
    return 90.0


def main():
    args = parse_args()
    total_invalidations = 0
    total_bytes = 0
    input_error = None

    try:
        with open(args.csv_file, "r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                total_invalidations += int(row["invalidations"])
                total_bytes += int(row["bytes"])
    except OSError as exc:
        input_error = exc

    if total_invalidations == 0 and total_bytes == 0:
        if input_error is not None:
            print(f"warning=input_unavailable:{input_error}", file=sys.stderr)
        else:
            print("warning=no_events_observed", file=sys.stderr)

    cpu_count = os.cpu_count() or 1
    invalidations_per_sec_raw = total_invalidations / args.window_seconds
    bytes_per_sec_raw = total_bytes / args.window_seconds
    invalidations_per_sec_per_core = invalidations_per_sec_raw / cpu_count
    bytes_per_sec_per_core = bytes_per_sec_raw / cpu_count
    health_class = classify_per_core(invalidations_per_sec_per_core)
    health_score = score_from_class(health_class)

    print(f"cpu_count={cpu_count}")
    print(f"invalidations_per_sec_raw={invalidations_per_sec_raw:.2f}")
    print(f"invalidations_per_sec_per_core={invalidations_per_sec_per_core:.2f}")
    print(f"bytes_invalidated_per_sec_raw={bytes_per_sec_raw:.2f}")
    print(f"bytes_invalidated_per_sec_per_core={bytes_per_sec_per_core:.2f}")
    print(f"health_score={health_score:.2f}")
    print(f"health_class={health_class}")


if __name__ == "__main__":
    main()
