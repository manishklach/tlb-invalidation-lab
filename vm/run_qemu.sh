#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VM_DIR="${ROOT_DIR}/vm"
KERNEL_DIR="${KERNEL_DIR:-${VM_DIR}/linux}"
KERNEL_REPO="${KERNEL_REPO:-https://github.com/torvalds/linux.git}"
KERNEL_REF="${KERNEL_REF:-v6.6}"
ARCH="${ARCH:-x86_64}"
JOBS="${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)}"
QEMU_BIN="${QEMU_BIN:-qemu-system-x86_64}"
KERNEL_IMAGE="${KERNEL_IMAGE:-}"

require_tool() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "error: required tool '$1' not found" >&2
        exit 1
    fi
}

prepare_kernel_tree() {
    if [[ -n "${KERNEL_IMAGE}" ]]; then
        return
    fi

    require_tool git
    require_tool make

    if [[ ! -d "${KERNEL_DIR}/.git" ]]; then
        git clone --depth 1 --branch "${KERNEL_REF}" "${KERNEL_REPO}" "${KERNEL_DIR}"
    fi

    if [[ ! -f "${KERNEL_DIR}/.config" ]]; then
        make -C "${KERNEL_DIR}" ARCH=x86_64 defconfig
        "${KERNEL_DIR}/scripts/config" --file "${KERNEL_DIR}/.config" \
            -e BLK_DEV_INITRD \
            -e DEVTMPFS \
            -e DEVTMPFS_MOUNT \
            -e SERIAL_8250 \
            -e SERIAL_8250_CONSOLE
        make -C "${KERNEL_DIR}" ARCH=x86_64 olddefconfig
    fi

    if [[ ! -f "${KERNEL_DIR}/arch/x86/boot/bzImage" ]]; then
        make -C "${KERNEL_DIR}" ARCH=x86_64 -j"${JOBS}" bzImage
    fi

    KERNEL_IMAGE="${KERNEL_DIR}/arch/x86/boot/bzImage"
}

boot_qemu() {
    require_tool "${QEMU_BIN}"

    exec "${QEMU_BIN}" \
        -m 2G \
        -smp 4 \
        -kernel "${KERNEL_IMAGE}" \
        -append "console=ttyS0" \
        -nographic
}

prepare_kernel_tree
boot_qemu
