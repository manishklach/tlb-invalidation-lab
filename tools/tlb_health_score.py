#!/usr/bin/env python3
import argparse
import csv
import sys


def parse_args():
    parser = argparse.ArgumentParser(description="Compute a simple TLB health score")
    parser.add_argument("csv_file", help="aggregated CSV from parse_trace.py")
    parser.add_argument("--window-seconds", type=float, default=10.0,
                        help="observation window in seconds")
    return parser.parse_args()


def classify(score):
    if score < 35:
        return "green"
    if score < 70:
        return "yellow"
    return "red"


def main():
    args = parse_args()

    total_invalidations = 0
    total_bytes = 0
    weighted_fanout = 0.0

    with open(args.csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            inv = int(row["tlb_invalidations"])
            total_invalidations += inv
            total_bytes += int(row["bytes_invalidated"])
            weighted_fanout += float(row["avg_fanout"]) * inv

    if total_invalidations == 0 and total_bytes == 0:
        print("warning=no_events_observed", file=sys.stderr)

    invalidations_per_sec = total_invalidations / args.window_seconds
    bytes_per_sec = total_bytes / args.window_seconds
    avg_fanout = 0.0
    if total_invalidations:
        avg_fanout = weighted_fanout / total_invalidations

    score = 0.0
    score += min(invalidations_per_sec / 1000.0, 1.0) * 40.0
    score += min(bytes_per_sec / (1 << 30), 1.0) * 35.0
    score += min(avg_fanout / 32.0, 1.0) * 25.0

    print(f"invalidations_per_sec={invalidations_per_sec:.2f}")
    print(f"bytes_invalidated_per_sec={bytes_per_sec:.2f}")
    print(f"avg_fanout={avg_fanout:.2f}")
    print(f"health_score={score:.2f}")
    print(f"health_class={classify(score)}")


if __name__ == "__main__":
    main()
