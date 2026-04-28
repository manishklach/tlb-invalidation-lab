#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${OUT_DIR:-${ROOT_DIR}/out}"
DURATION="${DURATION:-20}"
INTERVAL="${INTERVAL:-1}"
TRACE_PID=""
GPU_PID=""
SCHED_PID=""

cleanup() {
    local pids=("${GPU_PID}" "${SCHED_PID}")
    if [[ -n "${TRACE_PID}" ]]; then
        pids+=("${TRACE_PID}")
    fi
    for pid in "${pids[@]}"; do
        if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
            kill "${pid}" 2>/dev/null || true
            wait "${pid}" 2>/dev/null || true
        fi
    done
}

start_trace_collection() {
    local trace_cmd=()
    if [[ "${EUID}" -eq 0 ]]; then
        trace_cmd=(bash "${ROOT_DIR}/tools/collect_trace.sh" "${DURATION}")
    elif command -v sudo >/dev/null 2>&1; then
        trace_cmd=(sudo bash "${ROOT_DIR}/tools/collect_trace.sh" "${DURATION}")
    else
        echo "warning: trace collection skipped because root access is unavailable" >&2
        return
    fi

    (
        cd "${ROOT_DIR}"
        OUT_DIR="${OUT_DIR}" "${trace_cmd[@]}"
    ) &
    TRACE_PID="$!"
}

main() {
    trap cleanup EXIT INT TERM

    mkdir -p "${OUT_DIR}"

    echo "[1/7] starting TLB trace collection"
    start_trace_collection

    echo "[2/7] starting GPU sampler"
    python3 "${ROOT_DIR}/tools/sample_gpu.py" \
        --interval "${INTERVAL}" \
        --duration "${DURATION}" \
        --output "${OUT_DIR}/gpu_timeseries.csv" &
    GPU_PID="$!"

    echo "[3/7] starting scheduler sampler"
    python3 "${ROOT_DIR}/tools/sample_sched.py" \
        --interval "${INTERVAL}" \
        --duration "${DURATION}" \
        --output "${OUT_DIR}/sched_timeseries.csv" &
    SCHED_PID="$!"

    echo "[4/7] running benchmark suite"
    bash "${ROOT_DIR}/benchmarks/run_bench.sh" | tee "${OUT_DIR}/benchmark.log"

    echo "[5/7] waiting for samplers to finish"
    wait "${GPU_PID}" || true
    wait "${SCHED_PID}" || true
    if [[ -n "${TRACE_PID}" ]]; then
        wait "${TRACE_PID}" || true
    fi

    echo "[6/7] parsing and correlating data"
    python3 "${ROOT_DIR}/tools/parse_trace.py" "${OUT_DIR}/tlb_trace.txt" --csv "${OUT_DIR}/tlb_timeseries.csv" > "${OUT_DIR}/tlb_timeseries_stdout.csv"
    python3 "${ROOT_DIR}/tools/tlb_health_score.py" "${OUT_DIR}/tlb_timeseries.csv" --window-seconds "${DURATION}" > "${OUT_DIR}/health_score.txt"
    python3 "${ROOT_DIR}/tools/correlate_latency.py" \
        --tlb "${OUT_DIR}/tlb_timeseries.csv" \
        --gpu "${OUT_DIR}/gpu_timeseries.csv" \
        --sched "${OUT_DIR}/sched_timeseries.csv" \
        --output "${OUT_DIR}/correlation.csv" | tee "${OUT_DIR}/correlation_summary.txt"

    echo "[7/7] generating plots"
    python3 "${ROOT_DIR}/tools/plot_correlation.py" --input "${OUT_DIR}/correlation.csv" --output-dir "${OUT_DIR}/plots"

    echo
    echo "Experiment complete."
    echo "Next steps:"
    echo "  - review ${OUT_DIR}/health_score.txt"
    echo "  - inspect ${OUT_DIR}/correlation.csv"
    echo "  - open ${OUT_DIR}/plots/"
    echo "  - if you have latency data, rerun tools/correlate_latency.py with --latency"
}

main "$@"
