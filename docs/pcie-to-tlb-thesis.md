# PCIe to TLB Thesis

## Broader thesis

High-performance AI systems are often limited by hidden variables that sit outside the headline compute unit.

This repository is one piece of a broader operational thesis:

- PCIe errors degrade data movement efficiency
- TLB invalidation activity degrades translation continuity

Neither failure mode necessarily looks like a classic crash. Both can reduce effective compute capacity while leaving top-line utilization counters deceptively normal.

## PCIe side

At modern link rates, especially PCIe Gen5, signal-integrity margins become more important. When a system encounters link instability, it may:

- retrain
- downtrain
- fall back
- deliver lower effective bandwidth or higher jitter

The accelerator still exists. The server still boots. But useful data movement becomes less predictable.

## TLB side

Translation invalidation is a different subsystem, but the operational pattern is similar:

- the CPU is present
- the threads are runnable
- no obvious failure alarm appears
- yet useful work is repeatedly interrupted by invalidation maintenance

The result is not necessarily lower peak throughput in microbenchmarks. It is often:

- wider latency distribution
- straggler behavior
- reduced job-level efficiency

## Why treat them together

Both mechanisms affect the distance between nominal capacity and effective capacity.

They are hidden variables because:

- they often sit below normal application telemetry
- they can be bursty rather than constant
- their operational signature is often jitter, not catastrophe

That is why this repository is positioned as an observability and attribution tool. The first requirement for controlling hidden variables is making them visible enough to compare against real workload outcomes.
