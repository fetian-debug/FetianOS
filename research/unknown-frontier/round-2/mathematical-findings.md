# P2/P3 mathematical findings and novelty gate

## Exact retained-metadata model

[OBSERVED] A word x in F2^n is arbitrary. A trusted encoder stores f(x), then
noise produces z=x xor e for e in E_n={0,e_1,...,e_n,1^n}. The decoder sees
only z and f(x). Retained trusted metadata, not total workspace, is counted.
Two protected fault windows in the simulated reversible CNOT star induce E_n.
Faults inside gates, two faults or corrupt metadata are outside that guarantee.

[FORMALLY PROVEN — written argument] Define a graph on original words with
x adjacent to y exactly when x xor y is in (E_n xor E_n) minus {0}.
An r-bit metadata function permits zero-error decoding iff it is a proper
colouring using at most 2^r labels. Necessity: adjacent originals can produce
the same z, so equal metadata would be ambiguous. Sufficiency: for a received
z, list z xor E_n; a proper colour has exactly one consistent original.

[ESTABLISHED BY PRIOR WORK] This is the standard finite zero-error source/
side-information coding reduction, not a new computational architecture.
[Primary source](https://ieeexplore.ieee.org/document/1228155/).
A generic conventional graph-codebook baseline therefore has the same allowed
capability as every proposed encoder in this resource model. An efficiency
improvement would need a separate charged-cost claim; none is established here.

## All-encoder thresholds at five and six word bits

[FORMALLY PROVEN — written argument] At n=5, even-parity words form a clique
of size 16: nonzero differences have weight two or four, both in E_5 xor E_5.
Thus EVERY encoder, including nonlinear ones, requires at least four metadata
bits. The four-row construction with columns (1,2,3,4,8) separates all allowed
errors and supplies the matching upper bound.

[FORMALLY PROVEN — written argument] At n=6, E_6 itself is a clique of size
eight. Three metadata bits are necessary. Columns (1,2,3,4,5,6) assign distinct
syndromes to zero, every unit error and the full error (syndrome 7), so three
are sufficient. Thus the optimum drops from four bits to three when the
arbitrary borrowed word grows from five bits to six in this channel family.
The added bit is arbitrary and must also be restored; it is not a free zero.
The two comparisons have different word lengths and cannot establish a
same-resource superiority claim over a conventional decoder.

[FALSIFIED] H104's error-count-only formula predicts ceil(log2 7)=3 at n=5.
The clique proves this insufficient. [EXPERIMENTALLY DEMONSTRATED] Both Rust
and a generic graph-colouring/codebook baseline reach the true thresholds.
The two seeds each exercise all 1,184 allowed physical-event/input combinations.
The independently built codebook is optimal by the same clique certificates.
This defeats H105's capability-gap suggestion while preserving its true
functional threshold statement. Static codebook costs are recorded separately.

## H113: a general LINEAR-metadata family

[FORMALLY PROVEN — written algebra, not proof-assistant checked] For m>=3,
linear metadata needs exactly m+1 bits at n=2^m-3 and exactly m bits at
n=2^m-2. This is an internal derivation using classical parity-check arguments.
Publication priority of this exact formulation is UNVERIFIED.

For the first length, counting already requires r>=m. If r=m, all n columns
of a check matrix must be distinct and nonzero. Exactly two nonzero m-bit
vectors a,b are absent. Since XOR of all nonzero m-bit vectors is zero, XOR
of the used columns is a xor b. This vector is nonzero, distinct from a and b,
and therefore used. A full-word error aliases a unit error: impossible.
Consequently r>=m+1. For an upper bound, use columns 1,...,n, whose XOR is 1,
and append a single extra row selecting the column labelled 2. The only
low-syndrome collision, full error versus column 1, now has different extra
bits; all other allowed errors were already separated.

At the second length there is only one absent nonzero column a. XOR of the
used columns is a, so the full error has an unused nonzero syndrome. The m-bit
check works and counting requires m. This proves both linear bounds.

[EXPERIMENTALLY DEMONSTRATED] P3 validates 16 constructions for m=3..10,
checks 4,072 allowed error syndromes and 1,600 seeded random input/error cases.
[UNVERIFIED] This does NOT prove an all-encoder optimum for n=13 or larger.
Nor does it show a new capability beyond general error-set coding. The exact
priority question is separate from mathematical validity. Related inversion/
Hamming work exists; it is not safe to infer novelty from a missing exact title.
[Located related disclosure](https://www.vkit.ru/index.php/archive-rus/1437-034-040).

## Causal and sampling counterexamples

[FALSIFIED / written identification argument] H108 fails for Y=U versus
Y=X xor U with independent fair X,U. Both have the same observational law
and both do(X) marginals. Their individual response probabilities are zero
and one. A method seeing only those identical laws cannot identify which
response event holds. The eight assignments are retained. This is a known
nonidentification pattern, not a new estimator or an implementation win.
[Primary source](https://ftp.cs.ucla.edu/pub/stat_ser/r271-A.pdf).

[FALSIFIED / exact finite experiment] For H111, simultaneous updates using
match-neighbour probability 3/4 do not preserve the target joint law
(3/8,1/8,1/8,3/8). A sequential Gibbs sweep does. Rational matrices and an
independent 128-trajectory primitive-noise enumeration agree. Equal one-site
marginals do not establish the correct joint distribution. Parallel Gibbs
scheduling already addresses this distinction.
[Primary source](https://proceedings.mlr.press/v15/gonzalez11a.html).

[UNVERIFIED] No compiled-code correctness proof, physical error experiment,
quantum implementation, general catalytic-space separation or new computing
capability is established. The protected-metadata model is intentionally much
narrower than all working memory or an operating-system fault-tolerance claim.
