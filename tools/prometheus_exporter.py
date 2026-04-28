#!/usr/bin/env python3
import argparse
import csv
import http.server
import os
import socketserver
import threading
import time


def parse_args():
    parser = argparse.ArgumentParser(description="Expose TLB lab metrics for Prometheus")
    parser.add_argument("--input", required=True, help="time-series CSV from parse_trace.py")
    parser.add_argument("--listen", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9824)
    parser.add_argument("--window-seconds", type=float, default=10.0)
    parser.add_argument("--refresh-seconds", type=float, default=5.0)
    parser.add_argument("--max-process-labels", type=int, default=10)
    return parser.parse_args()


class MetricsState:
    def __init__(self):
        self.lock = threading.Lock()
        self.payload = ""

    def set_payload(self, payload):
        with self.lock:
            self.payload = payload

    def get_payload(self):
        with self.lock:
            return self.payload


def health_class_index(invalidations_per_sec_per_core):
    if invalidations_per_sec_per_core < 5.0:
        return 0
    if invalidations_per_sec_per_core <= 20.0:
        return 1
    return 2


def prometheus_escape(value):
    return value.replace("\\", "\\\\").replace("\"", "\\\"")


def build_metrics(csv_path, window_seconds, max_process_labels):
    total_invalidations = 0
    total_bytes = 0
    per_process = {}

    with open(csv_path, "r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            invalidations = int(row["invalidations"])
            bytes_invalidated = int(row["bytes"])
            pid = row["pid"]
            comm = row["comm"]
            key = (pid, comm)

            total_invalidations += invalidations
            total_bytes += bytes_invalidated
            if key not in per_process:
                per_process[key] = {"invalidations": 0, "bytes": 0}
            per_process[key]["invalidations"] += invalidations
            per_process[key]["bytes"] += bytes_invalidated

    cpu_count = os.cpu_count() or 1
    invalidation_rate = total_invalidations / window_seconds
    invalidation_rate_per_core = invalidation_rate / cpu_count
    score = 20.0 if invalidation_rate_per_core < 5.0 else 60.0 if invalidation_rate_per_core <= 20.0 else 90.0
    health_class = health_class_index(invalidation_rate_per_core)

    sorted_processes = sorted(
        per_process.items(),
        key=lambda item: item[1]["invalidations"],
        reverse=True,
    )
    top_processes = sorted_processes[:max_process_labels]
    other_invalidations = sum(item[1]["invalidations"] for item in sorted_processes[max_process_labels:])
    other_bytes = sum(item[1]["bytes"] for item in sorted_processes[max_process_labels:])

    lines = [
        "# HELP tlb_invalidations_total Total parsed TLB invalidations",
        "# TYPE tlb_invalidations_total counter",
        f"tlb_invalidations_total {total_invalidations}",
        "# HELP tlb_invalidation_rate TLB invalidations per second over the observation window",
        "# TYPE tlb_invalidation_rate gauge",
        f"tlb_invalidation_rate {invalidation_rate:.6f}",
        "# HELP tlb_invalidation_rate_per_core TLB invalidations per second normalized by CPU count",
        "# TYPE tlb_invalidation_rate_per_core gauge",
        f"tlb_invalidation_rate_per_core {invalidation_rate_per_core:.6f}",
        "# HELP tlb_bytes_invalidated Total bytes invalidated across parsed events",
        "# TYPE tlb_bytes_invalidated counter",
        f"tlb_bytes_invalidated {total_bytes}",
        "# HELP tlb_health_score Derived TLB health score",
        "# TYPE tlb_health_score gauge",
        f"tlb_health_score {score:.6f}",
        "# HELP tlb_health_class Encoded health class: 0=green, 1=yellow, 2=red",
        "# TYPE tlb_health_class gauge",
        f"tlb_health_class {health_class}",
        "# HELP tlb_invalidations_total Total parsed TLB invalidations, including per-process labeled series",
        "# TYPE tlb_invalidations_total counter",
        "# HELP tlb_bytes_invalidated_by_process Total bytes invalidated by process",
        "# TYPE tlb_bytes_invalidated_by_process counter",
    ]

    for (pid, comm), values in top_processes:
        pid_value = prometheus_escape(pid)
        comm_value = prometheus_escape(comm)
        lines.append(
            f'tlb_invalidations_total{{pid="{pid_value}",comm="{comm_value}"}} {values["invalidations"]}'
        )
        lines.append(
            f'tlb_bytes_invalidated_by_process{{pid="{pid_value}",comm="{comm_value}"}} {values["bytes"]}'
        )

    lines.append(
        f'tlb_invalidations_total{{pid="other",comm="other"}} {other_invalidations}'
    )
    lines.append(
        f'tlb_bytes_invalidated_by_process{{pid="other",comm="other"}} {other_bytes}'
    )

    return "\n".join(lines) + "\n"


def start_refresher(args, state):
    def refresh_loop():
        while True:
            try:
                state.set_payload(build_metrics(args.input, args.window_seconds, args.max_process_labels))
            except Exception as exc:
                state.set_payload(
                    "# HELP tlb_exporter_error Exporter refresh failure\n"
                    "# TYPE tlb_exporter_error gauge\n"
                    "tlb_exporter_error 1\n"
                    f"# error {exc}\n"
                )
            time.sleep(args.refresh_seconds)

    thread = threading.Thread(target=refresh_loop, daemon=True)
    thread.start()


def make_handler(state):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/metrics":
                self.send_response(404)
                self.end_headers()
                return

            payload = state.get_payload().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, fmt, *args):
            return

    return Handler


def main():
    args = parse_args()
    state = MetricsState()
    try:
        state.set_payload(build_metrics(args.input, args.window_seconds, args.max_process_labels))
    except Exception as exc:
        state.set_payload(
            "# HELP tlb_exporter_error Exporter initialization failure\n"
            "# TYPE tlb_exporter_error gauge\n"
            "tlb_exporter_error 1\n"
            f"# error {exc}\n"
        )
    start_refresher(args, state)

    handler = make_handler(state)
    with socketserver.TCPServer((args.listen, args.port), handler) as httpd:
        print(f"listening on http://{args.listen}:{args.port}/metrics")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
