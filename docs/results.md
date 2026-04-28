# Synthetic Results Narrative

## Scope

This note is intentionally synthetic. It shows the kind of relationship this lab is meant to expose without claiming that the numbers below came from a production fleet.

## Scenario

The synthetic scenario is a userspace `mmap()` churn benchmark running alongside a latency-sensitive service thread on the same host. As the churn rate rises, the trace stream shows more frequent TLB invalidation and MMU notifier activity. The service does not fail, but its tail latency widens.

The point is not that `mmap()` churn always causes inference latency regressions. The point is that an observability path now exists to test whether the two move together on a real system.

## Synthetic table

| Phase | Workload profile | TLB invalidations / sec | Bytes invalidated / sec | Avg target CPU count | P99 request latency |
| --- | --- | ---: | ---: | ---: | ---: |
| A | steady baseline | 8 | 2.1 MiB | 3.2 | 41 ms |
| B | moderate mmap churn | 47 | 11.8 MiB | 7.6 | 58 ms |
| C | heavy mmap churn | 126 | 37.4 MiB | 14.1 | 96 ms |

## Interpretation

- Phase A represents a host with low translation churn and relatively stable latency.
- Phase B shows a moderate rise in invalidation rate and fanout, with a visible but not catastrophic increase in P99 latency.
- Phase C shows a much noisier MMU profile. Tail latency rises sharply even though the machine is still nominally healthy.

This is the kind of pattern the lab is designed to make attributable:

- not a proof that TLB invalidation is the only cause
- not a claim of universal behavior
- a concrete lead for deeper kernel and workload investigation
