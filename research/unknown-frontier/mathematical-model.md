# Mathematical model and restricted proof obligations

## H005: fixed-matrix real feasibility

Let b=(b0,...,b5). The inequalities are x<=b0, -x<=b1, y<=b2,
-y<=b3, x+y<=b4, -x-y<=b5. Their coefficient matrix A never changes.

[FORMALLY PROVEN — written elementary derivation, not proof-assistant checked]
Real feasibility is equivalent to all five quantities being nonnegative:

    b0+b1, b2+b3, b4+b5, b0+b2+b5, b1+b3+b4.

Necessity: add the corresponding two or three original inequalities; their
left sides cancel. Each is a nonnegative row dependency y with y^T A=0.

Sufficiency: let X=[-b1,b0], Y=[-b3,b2], T=[-b5,b4]. The first three
conditions make these intervals nonempty. The last two say the interval
X+Y=[-b1-b3,b0+b2] intersects T. Choose s in that intersection and set
x=max(-b1,s-b2), y=s-x. Because s is between the endpoints of X+Y,
-b1<=x<=b0 and -b3<=y<=b2; x+y=s belongs to T. Hence (x,y) is feasible.
This construction covers equality and lower-dimensional feasible sets.

[ESTABLISHED BY PRIOR WORK] This is a small Farkas/projection instance, not a
new theorem. The certificate classifier and ordinary interval baseline test
algebraically equivalent conditions. Both do zero online LP solves. Therefore
C2's baseline separation fails even if C1 passes every experiment. Fixed matrix
size means O(1) online work is not an asymptotic improvement over that baseline.

The independent oracle intersects every nonparallel pair of boundary lines with
exact rational arithmetic and checks the resulting point against all rows.
Any nonempty feasible set here is bounded by the four axis inequalities and
has a vertex, including degenerate segments/singletons. Thus an exact vertex
oracle is complete for this model. It is an independent geometry algorithm,
not a restatement of the five cuts. A separate finite integer-grid oracle is
used only for small integer-bounded fixtures; integer endpoints plus the sum
constraint ensure an integer witness exists whenever a real witness does here.

## H007/H010: information and action

[FORMALLY PROVEN — written set argument] If u belongs to the intersection of
safe-action sets for every x in the *complete* current belief B, the actual x
belongs to B and the transition model is correct, then applying u is safe for
one step. This is direct universal instantiation, not a novel controller.

The conclusion does not imply equal optimal cost. For hidden x in {-1,1},
actions {-1,0,1}, dynamics x'=x+u, target zero and cost |x'|, a fully informed
controller uses u=-x and has cost zero. Any one observation-free action cannot
achieve both u=1 and u=-1. Randomizing cannot give zero cost almost surely in
both states. Thus the universal full-information cost claim H010 is false.
A multi-step safety guarantee additionally needs invariant-set/viability checks;
one-step safety alone is not silently extended to infinite horizons.

## H014/H015: state-dependent commutativity

[FORMALLY PROVEN — written conditional argument] Swapping adjacent actions
preserves the final state if both remain enabled and commute at that state.
Extending this swap across arbitrary contexts requires the property at every
relevant reachable state, plus the observation semantics. This is standard POR.

Counterexample to extrapolating one observed state: a(x,y)=(y,y),
b(x,y)=(0,y), c(x,y)=(x,1), initially (0,0). Actions a and b commute initially.
After c they do not: c;a;b ends (0,1), c;b;a ends (1,1). A reduction that
orders a before b based only on the initial sample loses an outcome. This is a
finite sequentially consistent transition model, not an experimental claim
about Linux races, weak memory, or a new implementation of DPOR.
