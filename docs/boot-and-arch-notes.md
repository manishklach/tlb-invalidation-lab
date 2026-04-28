# Boot and architecture notes

## Why include boot paths at all

This repository is focused on observability in steady-state kernel MM paths, not on early boot modification. Even so, it helps to document where architecture-specific TLB handling logic begins.

## x86

Useful starting points:

- `arch/x86/kernel/head_64.S`
- `arch/x86/mm/tlb.c`

The first file is relevant for early boot and paging bring-up context. The second is the obvious steady-state location for invalidation-path instrumentation sketches.

## arm64

Useful starting points:

- `arch/arm64/kernel/head.S`
- `arch/arm64/mm/`

As on x86, the boot path is not being modified in this repository. The purpose of documenting it is orientation for future lab work, not to imply current boot-stage instrumentation.

## Current scope boundary

Current repository scope:

- steady-state observability patches and sketches
- userspace tooling
- educational architecture probe modules

Explicitly out of scope in the current pass:

- early boot patching
- architecture bring-up changes
- replacement of native kernel TLB helpers
