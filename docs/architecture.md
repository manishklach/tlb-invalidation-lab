# Architecture

## Overview

A virtual memory change becomes visible to execution through a sequence that is easy to summarize and hard to observe:

1. A mapping or permission change occurs.
2. The kernel updates page tables.
3. The kernel invalidates stale translations.
4. Other CPUs that may have cached those translations are notified.
5. Execution resumes with fresh translation state.

For this lab, the interesting part is not only the invalidation itself. It is the fanout, timing, and surrounding subsystem activity. The goal is to make those relationships inspectable, not to assert that every invalidation burst is harmful.

## Mapping change to invalidation

Common invalidation-producing events include:

- `munmap()`
- `mprotect()`
- `mremap()`
- page migration and unmap paths
- MMU notifier invalidation windows
- teardown of pinned or registered regions

These changes typically produce range-oriented invalidation behavior rather than isolated single-page events.

## TLB shootdowns

On SMP systems, one CPU changing a page-table entry may need to invalidate translations cached by other CPUs. That produces a shootdown pattern:

- local CPU performs the page-table update
- remote CPUs receive an invalidation request
- those CPUs interrupt useful work
- stale entries are invalidated
- control returns to normal execution

The cost depends on:

- range size
- number of target CPUs
- frequency of repetition
- concurrency with other system work

## IPI versus broadcast invalidation

Historically, many remote invalidation paths relied on IPIs. Newer hardware may support more efficient remote invalidation assistance, reducing the amount of explicit per-CPU interrupt work required for some cases.

This repo distinguishes between:

- behavioral observation: what invalidations happened
- capability exposure: what the platform says it can support

The sysfs sketch in patch `0004` only exposes capability indicators. It does not prove a specific path was taken for any given flush.

## PCID / ASID context

Modern CPUs reduce some translation overhead through tagging mechanisms such as PCID or ASID-like concepts, allowing translations to remain distinguishable across address-space changes. That helps avoid full translation disruption in some cases, but it does not eliminate the need for invalidation when mappings become stale or permissions change.

High level takeaway:

- tagging helps preserve useful TLB state
- invalidation is still required for correctness
- the remaining invalidation cost can still show up in tail latency

## Observability model

This repository focuses on four layers:

1. x86 TLB invalidation tracepoints
2. MMU notifier invalidation tracepoints
3. optional experimental per-process counters
4. userspace aggregation, scoring, and export

The intended workflow is:

- collect trace data with low semantic ambiguity
- aggregate per process and per source
- compare invalidation behavior with latency and throughput metrics
- investigate attribution, not just symptom curves

That distinction matters. This repository is about exposing a hidden source of variance so it can be analyzed alongside other evidence, not about claiming that TLB behavior alone explains workload performance.
