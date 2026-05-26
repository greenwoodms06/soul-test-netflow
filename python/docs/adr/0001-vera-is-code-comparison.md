# ADR-0001: VERA P6/P7 comparison is code-to-code, not benchmark validation

## Status

Accepted

## Context

netflow's headline credibility claim was "validated against the VERA Core Physics
Benchmark." An external reviewer (a CTF/COBRA-TF developer) questioned the rigor,
prompting an Emissary pass through the primary sources. The VERA specification
(Godfrey, CASL-U-2012-0131-004) states verbatim, for both Problem 6 and Problem 7,
"No reference solution exists for this problem at this time" (pp. 79, 81). P6/P7
define inputs only; every published P6/P7 *result* is itself a code solution
(MC21/CTF, MC21/COBRA-IE, MPACT/CTF). Reference-grade values (KENO-VI eigenvalues)
exist only for the simpler Problems 1-5.

Three terms had been conflated: **verification** (are the equations solved right?),
**validation** (are they the right equations vs reality?), and **code comparison**
(do we match another code's answer?). Several "validation" numbers were unsourced
or the wrong quantity: a 2474 K *centerline* where VERA reports *volume-average*;
an F_q of 2.6 where no F_q is published; an 8.3 K coolant spread where the
figure-derived value is 6.6 K (CTF/VERA) / 8.7 K (COBRA-IE); a -8566 pcm Doppler
magnitude produced by a toy 1-group slab.

## Decision

Frame all VERA P6/P7 results as **code-to-code comparison** against published
CTF/MPACT/COBRA-IE solutions, not validation against reference truth. No absolute
claim ships without a cited reference value and a computed error (held in
`references/`). Quantities are compared at their *published definition*
(volume-average, not centerline, fuel temperature). Genuine measured validation
would require single-rod fuel-temperature data (Halden IFA-432 / OECD-NEA IFPE),
which is access-restricted and deliberately out of scope (see `references/INDEX.md`
and the memory `netflow-validation-data-ceiling`). netflow's neutronics stays
verification-grade (analytic bare slab); it does not claim a VERA eigenvalue.

## Consequences

- The papers make a weaker but honest claim: **code comparison + verification**.
- Withdrawn permanently: centerline 2474 K, F_q 2.5-2.8/2.6, 8.3 K spread,
  -8566 pcm Doppler magnitude. Figures are regenerated to carry no withdrawn
  number (single source of truth = `netflow.bench.vera_codecompare`).
- Every quantitative claim is traceable to a held, cited source in `references/`.
- A future contributor cannot re-introduce "validated against VERA" without
  contradicting this record.
- The path to true validation (Halden/IFPE measured fuel temperature) is
  documented but blocked by data access; revisit if NEA-1488 is obtained.
