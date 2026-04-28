#!/usr/bin/env python3
import argparse
import csv
import re
import sys
from collections import defaultdict

TLB_RE = re.compile(
    r"tlb_invalidation:\s+pid=(?P<pid>\d+)\s+tgid=(?P<tgid>\d+)\s+comm=(?P<comm>\S+)\s+"
    r"start=0x(?P<start>[0-9a-fA-F]+)\s+end=0x(?P<end>[0-9a-fA-F]+)\s+"
    r"bytes=(?P<bytes>\d+)\s+target_cpu_count=(?P<fanout>\d+)\s+broadcast=(?P<broadcast>[01])"
)

MMU_RE = re.compile(
    r"mmu_notifier_invalidate_range:\s+pid=(?P<pid>\d+)\s+tgid=(?P<tgid>\d+)\s+comm=(?P<comm>\S+)\s+"
    r"start=0x(?P<start>[0-9a-fA-F]+)\s+end=0x(?P<end>[0-9a-fA-F]+)\s+"
    r"bytes=(?P<bytes>\d+)\s+phase=(?P<phase>start|end)"
)


def parse_args():
    parser = argparse.ArgumentParser(description="Parse tlb-invalidation trace output")
    parser.add_argument("trace", help="input trace text file")
    parser.add_argument("--csv", dest="csv_path", help="write aggregated CSV")
    return parser.parse_args()


def update_bucket(buckets, key, event_type, data):
    bucket = buckets[key]
    bucket["event_count"] += 1
    bucket["bytes_invalidated"] += int(data["bytes"])
    bucket["type_counts"][event_type] += 1

    if event_type == "tlb":
        bucket["fanout_total"] += int(data["fanout"])
        bucket["broadcast_count"] += int(data["broadcast"])
    else:
        if data["phase"] == "start":
            bucket["mmu_start_count"] += 1
        else:
            bucket["mmu_end_count"] += 1


def main():
    args = parse_args()
    buckets = defaultdict(lambda: {
        "pid": 0,
        "tgid": 0,
        "comm": "",
        "event_count": 0,
        "bytes_invalidated": 0,
        "fanout_total": 0,
        "broadcast_count": 0,
        "mmu_start_count": 0,
        "mmu_end_count": 0,
        "type_counts": defaultdict(int),
    })

    with open(args.trace, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            m = TLB_RE.search(line)
            if m:
                data = m.groupdict()
                key = (int(data["tgid"]), data["comm"])
                bucket = buckets[key]
                bucket["pid"] = int(data["pid"])
                bucket["tgid"] = int(data["tgid"])
                bucket["comm"] = data["comm"]
                update_bucket(buckets, key, "tlb", data)
                continue

            m = MMU_RE.search(line)
            if m:
                data = m.groupdict()
                key = (int(data["tgid"]), data["comm"])
                bucket = buckets[key]
                bucket["pid"] = int(data["pid"])
                bucket["tgid"] = int(data["tgid"])
                bucket["comm"] = data["comm"]
                update_bucket(buckets, key, "mmu", data)

    rows = []
    for _, bucket in sorted(buckets.items(), key=lambda item: item[1]["bytes_invalidated"], reverse=True):
        tlb_count = bucket["type_counts"]["tlb"]
        avg_fanout = 0.0
        if tlb_count:
            avg_fanout = bucket["fanout_total"] / tlb_count
        rows.append({
            "pid": bucket["pid"],
            "tgid": bucket["tgid"],
            "comm": bucket["comm"],
            "event_count": bucket["event_count"],
            "tlb_invalidations": tlb_count,
            "mmu_events": bucket["type_counts"]["mmu"],
            "mmu_start_count": bucket["mmu_start_count"],
            "mmu_end_count": bucket["mmu_end_count"],
            "bytes_invalidated": bucket["bytes_invalidated"],
            "avg_fanout": f"{avg_fanout:.2f}",
            "broadcast_count": bucket["broadcast_count"],
        })

    fieldnames = [
        "pid",
        "tgid",
        "comm",
        "event_count",
        "tlb_invalidations",
        "mmu_events",
        "mmu_start_count",
        "mmu_end_count",
        "bytes_invalidated",
        "avg_fanout",
        "broadcast_count",
    ]

    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

    if args.csv_path:
        with open(args.csv_path, "w", newline="", encoding="utf-8") as csvfile:
            csv_writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            csv_writer.writeheader()
            csv_writer.writerows(rows)


if __name__ == "__main__":
    main()
