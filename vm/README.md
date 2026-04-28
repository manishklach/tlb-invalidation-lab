# QEMU bootstrap

This directory provides a minimal x86-64 QEMU bootstrap for lab validation.

## What it does

- uses `KERNEL_IMAGE` directly if you already have a kernel image
- otherwise clones Linux `v6.6` into `vm/linux`
- generates a basic `defconfig`-based kernel config if needed
- builds `arch/x86/boot/bzImage` if it is not present
- boots QEMU with a serial console

## Quick start

```bash
cd vm
./run_qemu.sh
```

Default QEMU invocation:

```bash
qemu-system-x86_64 \
  -m 2G \
  -smp 4 \
  -kernel bzImage \
  -append "console=ttyS0" \
  -nographic
```

## Use an existing kernel image

```bash
KERNEL_IMAGE=/path/to/arch/x86/boot/bzImage ./run_qemu.sh
```

## Useful environment variables

- `KERNEL_DIR`
- `KERNEL_IMAGE`
- `KERNEL_REF`
- `KERNEL_REPO`
- `JOBS`
- `QEMU_BIN`

## Notes

- this is a lab bootstrap, not a full guest-image pipeline
- the script intentionally stays minimal and does not create a root filesystem
- use this to validate bootability and early kernel instrumentation workflows before moving to richer VM setups
