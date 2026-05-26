# Methods/validation paper — plan (Architect record)

Independent of the intro note (`netflow.tex`). New file: `netflow-methods.tex`.

## Why this paper exists

A CTF (COBRA-TF) developer reviewed the intro note and said, in effect: it reads
like an introduction, not a grounded capability. Specifically asked for:

- the residual equations actually being set up,
- how boundary conditions are handled,
- what closure models are used,
- more testing,
- and the load-bearing one: **the VERA section shows our results and asserts it
  "matches the pattern" but never compares against the published numbers — it
  doesn't show how well.**

## Frame (two levels)

- Immediate: intro note asserts capability; an expert cannot judge if it is real.
- Larger: a methods paper must let a stranger reconstruct the model and trust it.
  Trust currency = explicit residuals + BCs + cited closures + verification with
  convergence orders + validation as number-vs-number with error metrics.

## The crux (Skeptic)

The failure to avoid: a longer, equation-rich paper that *still* does not put
netflow numbers beside VERA numbers with an error metric. The quantitative
validation table/figure is load-bearing. The whole paper gates on obtaining
**real, attributable VERA reference values**. Until the Emissary returns them,
the validation section is a placeholder and the paper is not done.

## Section structure and evidence each section must carry

| § | Section | Must show | Evidence source | Data-dep? |
|---|---|---|---|---|
| 1 | Formulation | node/edge/KCL residual `F_i=source+Σin−Σout=0`; Newton + sparse Jacobian; Picard fallback | core code | no |
| 2 | Governing/residual eqs per domain | thermal, hydraulic, neutronic residuals written out; how each maps to the generic form | plugin edges | no |
| 3 | Boundary conditions | Dirichlet (fixed nodes), Neumann (source), inlet/outlet advection sink, ground node for absorption, eigenvalue closure | code | no |
| 4 | Closure models | conduction k(T) (Fink UO₂, Zr-4), pellet 4πkL, gap (geometric He+rad / empirical h_gap), convection (DB/Gnielinski), radiation, cross-flow Darcy, mixing, ρ(T) | edges + materials | no |
| 5 | Verification | analytic edge resistances; Jacobian vs FD ≤1e-5; k-eff O(Δ²) (9.7→0.1 pcm); energy balance to 6 sig figs; 107 tests | tests/VALIDATION.md | no |
| 6 | **Validation vs VERA** | netflow vs published VERA: fuel temp, coolant rise/spread, k-eff, F_q, Doppler coeff — **tables with error %, residual plots, honest discrepancy** | Emissary (Godfrey, Kelly et al.) | **YES** |
| 7 | Scope & limits | scalar-network bound (no momentum eq); single-phase; two-node pellet vs conductivity integral; calibrated cross-flow | expert-qa.md | no |

## Work split

- Data-independent (§1–5, 7): writable now from code I have read. Author these.
- Data-dependent (§6): blocked on the Emissary's VERA digest. Real numbers only —
  no fabricated reference values. Every VERA cell must carry a citation.

## Honest risk + fallback

VERA Problem 6/7 detailed distributions may not be fully public. If the Emissary
cannot source a given quantity:
- keep the comparisons we *can* source (peak centerline temp, F_q, Doppler
  trend, k-eff convergence) with explicit citations, and
- state plainly which VERA quantities we could not obtain, rather than implying a
  match we cannot back. The Skeptic's bar: no asserted agreement without a cited
  reference value and a computed error.
