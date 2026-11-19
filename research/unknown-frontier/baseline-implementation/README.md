# Baselines and fairness

[ESTABLISHED BY PRIOR WORK] Fixed polyhedron projection and nonnegative dual
certificates are standard mechanisms. `projection.rs` is an independently
written specialization to the experiment matrix, not a port or a benchmark
run of an external solver. Its input information, arithmetic domain and
preprocessing opportunity equal the prototype's. It already achieves zero
online LP solves. The candidate therefore cannot establish a new capability by
beating repeated generic feasibility solving.

[OBSERVED] `geometry.py` enumerates exact rational vertices as an independent
truth oracle. It is deliberately *not* the performance baseline. For the small
fixtures an integer-grid oracle separately validates that geometry result.
The experiment does not compare production solver latency, system scheduling,
energy, hardware failures, or real concurrent Linux programs.
