#!/usr/bin/env bash
set -euo pipefail

DURATION="${1:-10}"
OUT_DIR="${OUT_DIR:-out}"
OUT_FILE="${OUT_DIR}/tlb_trace.txt"
TRACEFS="${TRACEFS:-/sys/kernel/tracing}"

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo "collect_trace.sh must run as root" >&2
        exit 1
    fi
}

mount_tracefs() {
    if mountpoint -q "${TRACEFS}"; then
        return
    fi

    mkdir -p "${TRACEFS}"
    mount -t tracefs tracefs "${TRACEFS}"
}

enable_event() {
    local event="$1"
    if [[ ! -e "${TRACEFS}/events/${event}/enable" ]]; then
        echo "warning: trace event ${event} not found" >&2
        return
    fi
    echo 1 > "${TRACEFS}/events/${event}/enable"
}

disable_event() {
    local event="$1"
    if [[ -e "${TRACEFS}/events/${event}/enable" ]]; then
        echo 0 > "${TRACEFS}/events/${event}/enable"
    fi
}

cleanup() {
    disable_event "tlb/tlb_invalidation"
    disable_event "mmu/mmu_notifier_invalidate_range"
    echo 0 > "${TRACEFS}/tracing_on" 2>/dev/null || true
}

main() {
    require_root
    mount_tracefs
    mkdir -p "${OUT_DIR}"

    trap cleanup EXIT

    echo nop > "${TRACEFS}/current_tracer"
    : > "${TRACEFS}/trace"

    enable_event "tlb/tlb_invalidation"
    enable_event "mmu/mmu_notifier_invalidate_range"

    echo 1 > "${TRACEFS}/tracing_on"
    sleep "${DURATION}"
    echo 0 > "${TRACEFS}/tracing_on"

    cat "${TRACEFS}/trace" > "${OUT_FILE}"
    echo "trace written to ${OUT_FILE}"
}

main "$@"
