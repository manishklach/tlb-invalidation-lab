# QEMU Bootstrap

This directory provides a minimal x86-64 QEMU bootstrap for lab validation.

## ⚠️ Important Note on Interaction
This setup is designed as a **kernel boot smoke test**. By default, it does **not** provide a root filesystem (rootfs).
- The kernel will likely panic at the end of the boot sequence because it cannot find an `init` process.
- This is **intentional**. Use this script to verify that your patched kernel boots, handles early initialization, and emits instrumentation logs to the serial console.

## 🛠️ Optional Improvements
For a more interactive lab environment, you can provide a minimal `initramfs`:
1. Build a static BusyBox binary.
2. Package it into a CPIO archive.
3. Pass it to QEMU using the `-initrd` flag by modifying `run_qemu.sh`.

## What it does
- Uses `KERNEL_IMAGE` directly if you already have a kernel image.
- Otherwise clones Linux `v6.6` into `vm/linux`.
- Generates a basic `defconfig`-based kernel config if needed.
- Builds `arch/x86/boot/bzImage` if it is not present.
- Boots QEMU with a serial console.

## Quick start
```bash
cd vm
./run_qemu.sh
```

## Useful environment variables
- `KERNEL_DIR`: Override the Linux source directory.
- `KERNEL_IMAGE`: Path to an existing `bzImage`.
- `JOBS`: Parallelism for the kernel build (defaults to CPU count).
- `QEMU_BIN`: Path to the QEMU executable.

## Notes
- This is a lab bootstrap, not a full guest-image pipeline.
- The script intentionally stays minimal and does not create a root filesystem.
- Use this to validate bootability and early kernel instrumentation workflows before moving to richer VM setups.
