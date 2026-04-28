# PCIe to TLB Thesis

## Framing

This document explains the repository's broader systems framing. It is not an argument that PCIe behavior and TLB invalidation are equivalent, and it is not a claim that either one alone explains inference performance.

The narrower claim is simpler:

- both can behave like hidden capacity reducers
- both are easy to miss in application-level dashboards
- both are worth instrumenting when infrastructure feels slower than its obvious counters suggest

## PCIe side

At modern link rates, especially PCIe Gen5, signal-integrity margins matter. When a platform sees link instability, it may:

- retrain
- downtrain
- retry
- deliver lower effective bandwidth or higher variance than nominal link speed suggests

That does not always show up as a clean device failure. It often shows up as less predictable data movement.

## TLB side

Translation invalidation is a different mechanism, but it can have a similar operational shape:

- the machine looks up
- the threads are runnable
- the workload is still moving
- useful work is nevertheless being interrupted by MMU maintenance

Again, the observable symptom is often variance rather than collapse:

- wider latency spread
- straggler behavior
- lower effective job efficiency

## Why connect them at all

The useful commonality is not subsystem identity. It is observability posture.

Both are examples of infrastructure effects that can reduce effective compute capacity while hiding below the first layer of common dashboards. This lab exists to instrument one of those effects: translation invalidation and its surrounding MMU activity.

## Intended takeaway

The intended takeaway is intentionally modest:

- if you already suspect tail-latency amplification
- and if CPU-side memory-management work is a plausible contributor
- then measuring invalidation activity is often more credible than guessing from utilization counters alone
