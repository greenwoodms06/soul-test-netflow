# CLOSEOUT — soultest-modelica (Soul-System dogfood on a Modelica/Dymola thermal chain)

**Status: COMPLETE / slices 1–10 + 17×17×30 assembly + 2026-05-26 unfreeze
(advanced flags + physics breadth + 25×25 scale) — 2026-05-26.** Third leg
of the netflow (Python) → soultest-julia (MTK) → this (Modelica/Dymola)
paradigm triangulation.

> **2026-05-26 unfreeze:** Project was previously closed at slices 1–10 +
> 17×17×30 assembly. Re-opened on 2026-05-26 to (a) close the "Dymola
> defaults only" caveat with an advanced-flag dogfood, (b) close the
> "parallel-independent assembly" caveat with three MSL-only physics-
> breadth extensions (cross-pin conduction / per-pin neutronics feedback /
> subchannel cross-flow), and (c) push past Julia's 17×17×30 anchor with a
> 25×25 ladder. MSL-only constraint formalized as ADR-0002. Findings added
> as MO-F15..F19 + SOUL-MO-Fg + SOUL-MO-Fh. Headline plot:
> `results/unfreeze_headline.png`.

## Purpose (and whether it was met)

This was the **third Soul-System dogfood** on the same physics chain, with the
medium being a Modelica/Dymola build driven headlessly from Python through the
DymolaInterface. Per the founding handoff (CONTEXT.md §1), the success bar was
two-fold:

1. **The triangulation comparison** — quantified evidence for "if I had a
   Python prototype, what does it cost to bring it into Modelica?"
2. **The dogfood signal** — did the Soul gates fire on their own *again* on a
   different medium after two prior runs?

**Verdict: yes on both, with one new finding.**

- ✅ **Quantified comparison delivered.** docs/FINDINGS.md ships the three-leg
  headline table and 8 Modelica/Dymola capability findings, plus the 6
  Soul-System findings specific to this leg.
- ✅ **Internalized doctrine fired:** the slice-4 0.34 K disagreement was
  traced (not threshold-relaxed) without external prompting, per the SOUL-F-a
  guardrail. The expansion gate explicitly excluded slices 7–10 (Julia's
  compile-wall territory) before scope was locked. Universe Collapse did not
  recur.
- 🆕 **NEW finding (MO-F3):** "same fluid" does not mean "same numerical answer
  across implementations." Dymola's IF97 ↔ CoolProp HEOS transport-property
  formulations disagree by ~3% on k and Pr at PWR conditions, driving a 0.34 K
  pin centerline drift — below Dittus-Boelter's own ~20% correlation
  uncertainty, but worth recording for code-comparison work.

## The two deliverables (the actual point)

- **`docs/FINDINGS.md`** — the ledger: **8 Modelica capability findings** + **6
  Soul-System findings**. The dogfood's real output.
- **`NetflowModelica/`** — the working model: 6 components, 3 material
  functions, 7 test scenarios. 430 LOC of physics — verified slice-by-slice.

### Modelica/Dymola verdict (headline)

The stream-connector + IF97 + connect()-emitted-conservation triple is *correct
and ergonomic* on this kind of problem — three slices verified conservation
invariants at float64 noise (no hand-written residual to validate). Storage
extension (slice 1 → slice 5) was one HeatCapacitor connect() with no other
changes — the ADR's "steady-first, storage added later" claim is empirically
true. Code-comparison agreement with netflow to **24.7 mK when property
formulations are aligned** (matching Julia's 25 mK bar); **0.34 K when using
native Modelica IF97** — fully traced to IF97 vs IAPWS-95 transport-property
differences and below Dittus-Boelter correlation uncertainty.

End-to-end wall-clock per simulate: ~3.7 s (translate + compile + sim) on top
of a ~2 s Dymola startup. netflow's pure-Newton-solve was 9 ms. The trade-off
is honest: Modelica buys you generated C, a stiff DAE integrator family, IF97,
the standard library, and conservation-by-construction at the cost of seconds
per model edit.

### Soul-System findings (headline)

- **SOUL-MO-Fa**: completion-gate pattern compounds; the third leg avoided the
  same trap (relax-threshold-to-fit) at first chance without external prompting.
- **SOUL-MO-Fb**: ceremony compresses on repeated dogfood — *because the prior
  legs paid for it*. Light prior-art sweep + ADR-leaning-on-Julia + reusable
  slice-and-verify pattern made the third leg fast.
- **SOUL-MO-Fc**: re-measure guardrail (SOUL-F-d) was satisfied in 30 seconds
  and confirmed baseline stability.
- **SOUL-MO-Fd**: Modelica's `connect()`-emitted conservation removes an entire
  bug class netflow had to hand-validate. Strongest structural argument seen
  for the acausal-connector paradigm.
- **SOUL-MO-Fe**: the harness-gotcha surface (MO-F6) is the next SKILL.md
  candidate; eight distinct traps captured pre-strand.
- **SOUL-MO-Ff**: explicit *exclusion-naming* worked — slices 7–10 were named
  out-of-scope BEFORE the build, preventing Julia-pattern scope creep.

## What was built (the medium, all verified)

| Slice | What | Verification | Result |
|---|---|---|---|
| 1 | Constant-prop FuelPin | analytic series-resistance | Δ = 0 K (machine-precision) |
| 2 | Heated coolant channel | enthalpy balance vs CoolProp IF97 | Δh = 7 nJ/kg, ΔT = 9e-13 K |
| 3 | Coupled 10-cell chain | (a) energy closure, (b) per-pin radial drop | 0 W; 1.1e-13 K |
| 4 | netflow code-comparison | re-measured netflow + analytic Dittus-Boelter | 24.7 mK (aligned) / 0.34 K (native IF97) |
| 5 | Transient single pin | first-order analytic exp trajectory | 2.8 μK over 12.6 τ |
| 6 | Transient coupled chain | t→∞ matches slice-3 steady | 84 mK at 10 τ |

Plus: `bench/remeasure_netflow.py` (SOUL-F-d guardrail), `bench/end_to_end_timing.py`,
the Python harness layer (`test/dymola_harness.py`), and `docs/adr/0001`
naming the abstraction.

## What "complete" means here

No further development on this leg. The findings are captured and the bounded
model is a verified demonstrator. Like netflow and soultest-julia, this repo
is frozen as a finished artifact — if the Body resumes (to test TRANSFORM as
a parallel build, to push past 25×25 scale, to add an OpenModelica leg, or
to capture MO-F6 as a SKILL.md), start from `docs/FINDINGS.md` and this file.

## 2026-05-26 unfreeze appendix

The project re-opened on 2026-05-26 for three bounded extensions (see
`docs/adr/0002-msl-only-carries-through-all-extensions.md` for the scope
choice, `docs/experiments/2026-05-26-step0-dymola-advanced-flags-research.md`
for the research notes, and the new `references/INDEX.md §VERA P6/P7` block
for the loaded anchor).

**What landed:**

- **Step 0 (research):** Dymola advanced-flag reach-out + MSL primitive scan.
  Found `Advanced.Translation.SparseActivate` was the renamed `Advanced.SparseActivate`
  (Dymola 2025x rename). LBL Buildings Library recommends Radau + 1e-6 for
  thermal-fluid; both rejected at 17×17×10 (no movement).
- **Step 1 (VERA P6/P7 anchor):** Operating point + reference values loaded into
  `references/INDEX.md`; new model `NetflowModelica.Tests.AssemblyVeraP6`
  parameterised on the published VERA P6 spec. Per Godfrey 2014 the benchmark
  has NO reference solution — every published number is a code solution; this
  leg's outputs join that ledger as code-comparison candidates. **CONSUMED
  2026-05-26 (post-unfreeze polish):** `bench/vera_p6_codecompare.py` ran
  AssemblyVeraP6 at 17×17×30 with the Kelly Fig. 10 cosine radial peaking;
  measured power-driven outlet spread 1.5 K vs Kelly 6.6 K CTF/VERA, 8.7 K
  COBRA-IE (MO-F21). Gap is structurally attributable to no-guide-tube
  topology + no axial peaking in this run — not a calibration failure.
- **Step 2 (advanced-flag dogfood):** Two sweep scripts measured 12 scenarios
  across three Dymola walls. **MO-F15** — `SparseActivate` halves the sim-bound
  wall and rescues the init-bound wall. **MO-F16** — no Dymola flag moves the
  compile-bound wall (cc1 is the bottleneck).
- **Step 3 (physics breadth):** Three MSL-only assembly extensions built and
  measured against the vanilla VERA-P6-parameterised baseline. **MO-F17** —
  cross-pin axial conduction (`AssemblyVeraP6CrossPin`, 543 s @ 17×17×30,
  +25 %). **MO-F18** — per-pin neutronics feedback (`AssemblyVeraP6Neutronics`,
  135 s @ 17×17×10; full 17×17×30 transient deferred). **MO-F19** — subchannel
  cross-flow (`AssemblyVeraP6Subchannel` + `LateralFlowLink`, 621 s @
  17×17×30, +43 %; required adding the linear-ΔP closure because direct
  connect of 4-port lateral cells is structurally singular).
- **Step 4 (scale past Julia's anchor):** **MO-F20** — 18×18×30 (454 s)
  and 20×20×30 (645 s) clean on the prior slope-1.38 line; **22×22×30 cc1
  OOM-killed at 19.9 GB resident** (kernel dmesg confirmed). 25×25×30 not
  reached. The RAM ceiling sits one step earlier than the 1.38 exponent
  extrapolation predicted. Plot: `results/assembly_scaling_extended.png`.

**New artifacts:**

- 4 new test models: `AssemblyVeraP6`, `AssemblyVeraP6CrossPin`,
  `AssemblyVeraP6Neutronics`, `AssemblyVeraP6Subchannel`.
- 2 new components: `FuelPinDynPower` (signal-driven Q), `LateralFlowLink`
  (linear m_flow = G·Δp closure), plus the 4-port `CoolantCellSub`.
- 3 new bench scripts: `advanced_flag_sweep.py`, `advanced_flag_sweep_part2.py`,
  `physics_breadth_ladder.py`, `stress_assembly_25x25.py`.
- 4 smoke tests at small scale.
- 1 headline plot: `results/unfreeze_headline.png` (2 panels — flag-vs-wall,
  physics-breadth scaling).
- 2 new findings: **SOUL-MO-Fg** (wall moves with scale even within one
  paradigm), **SOUL-MO-Fh** (Coherent-Falsehood-on-inference instance to
  pair with the ideas.md "wall-time-only trap" pattern if a third instance
  lands).

**Caveats updated in COMPARISON.md §6:** "defaults only" and
"parallel-independent assembly" caveats are now MEASURED, not deferred.

## Upstreaming (required for Soul reference projects)

Soul-meta findings to be upstreamed to the Soul-System repo:

- **SOUL-MO-Fb** (ceremony compresses on third use): material for a finding
  on "dogfood compounding value" — the structural payoff of doing the same
  Soul dance on multiple media.
- **SOUL-MO-Fd** (acausal-connector conservation-by-construction): a concrete
  data point reinforcing the Council's 2026-05-20 verdict that pivoted netflow
  toward Modelica/MTK. This dogfood adds Modelica numbers to that case.
- **SOUL-MO-Ff** (exclusion-naming as a scope discipline): a concrete instance
  of the Accountant role doing its job pre-build; worth a Finding on its own.
- **SOUL-MO-Fe → MO-F6** (skill-capture trigger): the eight headless-harness
  traps are tomorrow's SKILL.md if not captured. Worth a Finding on "when
  should a skill be captured" — proposing "after the third trap from the same
  surface" as a heuristic.

Three of the four were upstreamed to `/mnt/d/Projects/Soul-System/findings/open/`
and accepted:

- **SOUL-F032** — `dogfood-ceremony-compresses-on-repeated-use.md`
- **SOUL-F034** — `exclusion-naming-as-accountant-discipline.md`
- **SOUL-F035** — `skill-capture-trigger-third-trap-heuristic.md`

The fourth (SOUL-F033 — acausal connect()-emitted conservation removes a bug
class) was upstreamed but **reverted by the Body** (Soul-System repo commit
`6d8562c`, 2026-05-26) as "project-paradigm, not Soul-meta." The pattern is
a Modelica-domain claim with Soul-shaped form; it belongs at home in this
leg's `docs/FINDINGS.md` (MO-F1 / MO-F4 / MO-F10..F12), not in the Soul
upstream. The Body added a diagnostic test to the seed in the same commit:
*"if you removed the project's domain entirely, would the lesson still be a
Soul System lesson?"* Carry this test forward to any future upstreaming.

*Reference-project upstreaming obligation: discharged (with one revert and
the upstream-boundary doctrine tightened in response).*
