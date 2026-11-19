# P3: algebraic extension after the finite P2 result

[HYPOTHESIS H113] Let E_n={0,e_1,...,e_n,1^n}. For every integer m>=3,
the minimum number of LINEAR retained protected-metadata bits for exact
restoration is m+1 when n=2^m-3, and m when n=2^m-2.

This is a new separately registered conjecture in this investigation, not a
revision of failed H104 or accepted proof of a new computing capability.
Original H101–H112 and P2 remain unchanged. Nonlinear encoders are excluded
from this statement; no all-encoder claim at n=13 or above is authorized.

[HYPOTHESIS] Lower-bound attempt: m-bit linear checks must give n distinct
nonzero columns. At n=2^m-3 exactly two nonzero columns a,b are absent. XOR of
all used columns is a xor b, which is nonzero and used. The full-word error
therefore collides with a unit error. Upper-bound attempt: columns 1..n and
one extra row on the column labelled 2 separate that collision. At n=2^m-2,
columns 1..n alone have XOR equal to the unique absent nonzero column.

Test protocol: before execution record this file's hash. For m=3..10,
construct the matrices, enumerate all allowed effective error masks through an
independent row-parity implementation, test proposed-code injectivity and the
m-bit truncated-code collision, and test 100 seeded random initial words per
(m,n) pair. Record every case. This is validation of an algebraic construction,
not enumeration of every possible matrix for large m or physical circuitry.
A written proof must separately justify the universal linear lower bound.

Novelty gate: investigate general additive error-set coding, Hamming parity
checks, inversion/complement correction, zero-error side-information coding and
folded-cube graph formulations. A new example or shortened-Hamming construction
is not automatically an unavailable computing capability. No runtime integration.
