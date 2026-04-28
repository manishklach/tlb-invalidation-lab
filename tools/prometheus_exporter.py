#!/usr/bin/env python3
import argparse
import csv
import http.server
import socketserver
import threading
import time


def parse_args():
    parser = argparse.ArgumentParser(description="Expose TLB lab metrics for Prometheus")
    parser.add_argument("--input", required=True, help="aggregated CSV from parse_trace.py")
    parser.add_argument("--listen", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9824)
    parser.add_argument("--window-seconds", type=float, default=10.0)
    parser.add_argument("--refresh-seconds", type=float, default=5.0)
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


def classify(score):
    if score < 35:
        return 0
    if score < 70:
        return 1
    return 2


def build_metrics(csv_path, window_seconds):
    total_invalidations = 0
    total_bytes = 0
    weighted_fanout = 0.0

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            inv = int(row["tlb_invalidations"])
            total_invalidations += inv
            total_bytes += int(row["bytes_invalidated"])
            weighted_fanout += float(row["avg_fanout"]) * inv

    invalidation_rate = total_invalidations / window_seconds
    avg_fanout = weighted_fanout / total_invalidations if total_invalidations else 0.0

    score = 0.0
    score += min(invalidation_rate / 1000.0, 1.0) * 40.0
    score += min((total_bytes / window_seconds) / (1 << 30), 1.0) * 35.0
    score += min(avg_fanout / 32.0, 1.0) * 25.0

    lines = [
        "# HELP tlb_invalidations_total Total parsed TLB invalidations",
        "# TYPE tlb_invalidations_total counter",
        f"tlb_invalidations_total {total_invalidations}",
        "# HELP tlb_invalidation_rate TLB invalidations per second over the observation window",
        "# TYPE tlb_invalidation_rate gauge",
        f"tlb_invalidation_rate {invalidation_rate:.6f}",
        "# HELP tlb_bytes_invalidated Total bytes invalidated across parsed events",
        "# TYPE tlb_bytes_invalidated counter",
        f"tlb_bytes_invalidated {total_bytes}",
        "# HELP tlb_health_score Derived TLB health score",
        "# TYPE tlb_health_score gauge",
        f"tlb_health_score {score:.6f}",
        "# HELP tlb_health_class Encoded health class: 0=green, 1=yellow, 2=red",
        "# TYPE tlb_health_class gauge",
        f"tlb_health_class {classify(score)}",
    ]
    return "\n".join(lines) + "\n"


def start_refresher(args, state):
    def refresh_loop():
        while True:
            try:
                state.set_payload(build_metrics(args.input, args.window_seconds))
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
    state.set_payload(build_metrics(args.input, args.window_seconds))
    start_refresher(args, state)

    handler = make_handler(state)
    with socketserver.TCPServer((args.listen, args.port), handler) as httpd:
        print(f"listening on http://{args.listen}:{args.port}/metrics")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
