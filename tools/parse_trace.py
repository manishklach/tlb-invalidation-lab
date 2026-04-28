#!/usr/bin/env python3
import argparse
import csv
import math
import re
import sys
from collections import defaultdict

LINE_RE = re.compile(
    r"^\S+\s+\[\d+\]\s+\S+\s+(?P<timestamp>\d+\.\d+):\s+"
    r"(?P<event>tlb_invalidation|mmu_notifier_invalidate_range):\s+"
    r"pid=(?P<pid>\d+)\s+tgid=(?P<tgid>\d+)\s+comm=(?P<comm>\S+)\s+"
    r"start=0x(?P<start>[0-9a-fA-F]+)\s+end=0x(?P<end>[0-9a-fA-F]+)\s+"
    r"bytes=(?P<bytes>\d+)"
    r"(?:\s+target_cpu_count=(?P<fanout>\d+)\s+broadcast=(?P<broadcast>[01]))?"
    r"(?:\s+phase=(?P<phase>start|end))?"
)


def parse_args():
    parser = argparse.ArgumentParser(description="Parse tlb-invalidation trace output")
    parser.add_argument("trace", help="input trace text file")
    parser.add_argument("--csv", dest="csv_path", help="write time-series CSV")
    return parser.parse_args()


def make_writer(handle):
    fieldnames = [
        "timestamp",
        "pid",
        "comm",
        "invalidations",
        "bytes",
        "invalidations_per_sec",
        "bytes_invalidated_per_sec",
    ]
    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    return writer


def main():
    args = parse_args()
    buckets = defaultdict(lambda: {
        "timestamp": 0,
        "pid": 0,
        "comm": "",
        "invalidations": 0,
        "bytes": 0,
    })
    matched = 0
    input_error = None

    try:
        with open(args.trace, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                match = LINE_RE.search(line)
                if not match:
                    continue

                data = match.groupdict()
                bucket_ts = int(math.floor(float(data["timestamp"])))
                key = (bucket_ts, int(data["pid"]), data["comm"])
                bucket = buckets[key]
                bucket["timestamp"] = bucket_ts
                bucket["pid"] = int(data["pid"])
                bucket["comm"] = data["comm"]
                bucket["bytes"] += int(data["bytes"])
                if data["event"] == "tlb_invalidation":
                    bucket["invalidations"] += 1
                matched += 1
    except OSError as exc:
        input_error = exc

    rows = []
    for _, bucket in sorted(buckets.items(), key=lambda item: (item[1]["timestamp"], item[1]["pid"], item[1]["comm"])):
        rows.append({
            "timestamp": bucket["timestamp"],
            "pid": bucket["pid"],
            "comm": bucket["comm"],
            "invalidations": bucket["invalidations"],
            "bytes": bucket["bytes"],
            "invalidations_per_sec": f"{float(bucket['invalidations']):.2f}",
            "bytes_invalidated_per_sec": f"{float(bucket['bytes']):.2f}",
        })

    writer = make_writer(sys.stdout)
    writer.writerows(rows)

    if args.csv_path:
        with open(args.csv_path, "w", newline="", encoding="utf-8") as handle:
            csv_writer = make_writer(handle)
            csv_writer.writerows(rows)

    if input_error is not None:
        print(f"warning: unable to read trace input {args.trace}: {input_error}", file=sys.stderr)
    elif matched == 0:
        print("warning: no matching tlb/mmu tracepoint events found", file=sys.stderr)


if __name__ == "__main__":
    main()
