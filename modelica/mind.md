# The Mind — soultest-modelica

This is the project-specific compressed-rules artifact for the soultest-modelica
Modelica/Dymola thermal-chain dogfood (third leg of the netflow → Julia →
Modelica paradigm triangulation; FROZEN per CLOSEOUT.md). Always-on (loaded
after the seed via `@mind.md` in `CLAUDE.md`). Holds **doctrine** — rules that
apply across contexts in this project's domain (Modelica/Dymola simulation,
IF97 properties, code-comparison work). Specific obligations and particular
results stay in the records (`docs/FINDINGS.md`, `CLOSEOUT.md`, `test/`). The
Mind names the rule; the record carries the specifics.

## Rules (generators)

A rule produces decisions, not a description of one.

1. **Use MSL primitives; don't reinvent.** `HeatPort_a/b`, `FluidPort_a/b`,
   `HeatCapacitor`, `ThermalConductor`, `Modelica.Media.Water.StandardWater` are
   pre-built and idiomatic. Reinventing them is the SOUL-F-c regretted decision
   the Julia leg recorded. *Source:* CONTEXT.md §2 + ADR-0001 + SOUL-F-c.

2. **Name the property-backend in any cross-tool comparison.** "Same fluid
   specified" does NOT mean "same numerical answer" — IF97 vs IAPWS-95 transport
   correlations disagree by ~3% on k and Pr at PWR film temperatures, driving
   a 0.34 K pin centerline drift. State the backend, state the gap. *Source:* MO-F3.

3. **Re-measure references before claiming agreement (SOUL-F-d).** Costs ~30 s,
   confirms baseline stability. Don't trust the record — even when the record
   is a prior leg's re-measurement. *Source:* SOUL-MO-Fc + SOUL-F-d.

4. **Storage extension is one `connect()` away — no topology change.** Slice 1's
   resistor stack becomes slice 5's transient by adding one `HeatCapacitor` on
   the centerline port. Validates ADR-0001's "steady-first, storage later"
   claim empirically. *Source:* MO-F4.

5. **Set ONE of (m_flow, p) at a source — never both.** A FluidPort source
   over-determines a pressure-coupled network without momentum. The Julia
   attempt avoided this by separating MassFlowInlet from PressureOutlet.
   *Source:* MO-F6.

6. **`experimentSetupOutput(doublePrecision=True)` before any μK-level
   verification.** Default `.mat` is single-precision compressed; conservation
   work at noise level needs full doubles. *Source:* MO-F6.

7. **`replaceable Medium` + Boolean parameter switch is the right pattern for
   comparing two property formulations in one component.** No code duplication;
   both code paths compile. Lets one slice ship two results. *Source:* MO-F8.

8. **Name where YOUR wall lives.** Different paradigms have different walls:
   netflow → sparse-LU at ~10⁶ nodes; Julia/MTK → `mtkcompile` scalarisation
   ~N^1.6; Dymola → gcc cc1 codegen (~5 min, 174 MB C, 11.7 GB RAM at 17×17×30).
   The wall MOVES with paradigm; name yours before claiming scaling.
   *Source:* MO-F13/F14.

9. **`/soul-verify` before claiming a wall-time-only success — measurement of
   meta-properties (time, size, log output) without measurement of physics is
   Coherent Falsehood at the bench.** A stress test that measured wall-time and
   called complete would have passed a garbage-producing run. *Source:*
   ideas.md "Coherent Falsehood on measurement" entry.

10. **Verification ≠ Validation ≠ Code-comparison — be precise in writing.**
    Verification = matches textbook closed form. Code-comparison = matches
    another implementation (netflow). Validation = matches measured reality
    (data-ceiling not crossed in this project). Never "validation" without
    measured data. *Source:* CONTEXT.md §7.

## Tensions (recurring pulls)

- **MSL primitives ↔ hand-rolled.** Julia's lesson is *use MSL* (Rule #1). But
  bespoke surfaces (e.g. the FuelPin geometry — small analytic resistance) are
  honestly faster hand-rolled. The boundary: if MSL has it, use it; if MSL
  doesn't, the marginal LOC is small.

- **Compile-time cost ↔ runtime ergonomics.** Dymola buys IF97 + connect-and-go
  conservation + DAE integrators + generated C at the price of ~3.7 s codegen
  per model edit. netflow's 9 ms is just the Newton solve. Both honest; pick
  consciously.

- **Bounded scope ↔ research questions.** Slices 1–6 = dogfood deliverable;
  slices 7–10 = "is Dymola's compile-wall further than Julia's?" is its OWN
  research question, deliberately deferred. Confusing the two is the scope-
  creep trap (Julia's lesson — added slices 7–10 past plan).

- **IF97 ↔ HEOS — same fluid, different numbers.** Both correct implementations
  of their respective standards (IAPWS-IF97 R12/R15 transport vs IAPWS-95).
  Neither is wrong; the 0.34 K gap is real and BELOW Dittus-Boelter's ~20%
  correlation uncertainty. Always state which backend.

- **Build-time-cheap-to-dogfood ↔ bench-time-out-of-scope.** Soul ceremony is
  the cheap part (CONTEXT.md + ADR + light sweep + slice-by-slice verify);
  bench scaling is the deliberately-excluded part. Don't conflate.

## Invariants (cannot vary without breaking the project)

- **Property-backend must be named when comparing across tools.** Else
  MO-F3-class confusion is unavoidable.

- **`connect()` emits conservation; never write Σf = 0 by hand in Modelica.**
  That is the bug class the acausal paradigm makes structurally impossible.

- **Verification, validation, and code-comparison are distinct.** Word choice
  is load-bearing in CLOSEOUT.md / FINDINGS.md.

- **The data-ceiling guardrail holds.** Measured fuel-pin data is full-core or
  NEA-restricted. This project does code-comparison only — never claims
  validation.

- **Re-measure don't trust the record (SOUL-F-d).** Even prior-leg
  re-measurements get re-checked before being treated as the reference.

## Contrast cases (disambiguating examples)

- **MO-F2 vs MO-F3 — aligned vs native property backends.** Same physics, same
  slice 4. With aligned CoolProp-HEOS quadratic fits: 24.7 mK match (Julia's
  bar). With native Modelica IF97: 0.34 K drift, fully traced to transport-
  property formulations. **The disambiguating rule:** name the backend; both
  are correct; the gap is below correlation uncertainty.

- **Julia's compile-wall vs Modelica's gcc-cc1-wall — the wall moves with
  paradigm.** Julia: `mtkcompile` scalarisation per component, ~N^1.6,
  extrapolated 25-40 min at 17×17×30 (never run). Modelica/Dymola: completed
  17×17×30 in 397 s end-to-end; **the dominant cost was `gcc -O1 cc1` (11.7
  GB RAM, ~5 min) on 174 MB of generated C**. Different paradigms, different
  walls.

- **Slice 1 → slice 5 (one HeatCapacitor `connect()`) vs hand-rolled where
  storage = new equations.** ADR-0001's claim verified empirically: connect-
  and-extend is the property; hand-rolled is the regressive form.

- **Setting (m_flow + p) vs setting ONE — the over-determined source trap.**
  Sources should set EITHER mass flow OR pressure, not both. Julia avoided
  this by separating MassFlowInlet from PressureOutlet; Modelica has the same
  trap with the same fix.

- **Soul System F033 (reverted upstream) vs this project's MO-F1/F4 (stayed at
  home).** Both describe acausal-connect()-emitted conservation. F033 framed
  it as a Soul-meta rule ("prefer connect()-emitted conservation"); the Body
  reverted it as project-paradigm. **The disambiguating test** (added to the
  Soul seed §Reference Projects on 2026-05-26): *if you removed the project's
  domain entirely, would the lesson still be a Soul System lesson?* For
  acausal conservation — NO. It's Modelica-paradigm. Stays at home.

## Incompressible residual (named, not forced)

Some accumulated knowledge doesn't reduce to rules — try to compress it and
you lose load-bearing information. Honesty about the residual is part of the
Mind's discipline.

- **The specific timing numbers** (3.7 s per simulate, 397 s end-to-end at
  17×17×30, ~5 min gcc cc1, 174 MB C, 11.7 GB RAM). Historical anchors on
  this machine; useful as comparison points but not rules.

- **The specific match gaps** (24.7 mK aligned, 0.34 K native, 2.8 μK over
  12.6 τ). Particulars belong in `docs/FINDINGS.md` and `test/` outputs, not
  in the Mind.

- **The 8 harness gotchas (MO-F6).** Belong in a project-local SKILL.md
  (`headless-dymola-harness`) — the captured surface, not a rule. The Mind
  records the *pattern* (Rule #6, Rule #9); the SKILL.md (when written)
  carries the surface.

- **The slice-by-slice ladder** (slice 1 inputs, slice 4 baseline, slice 6
  trajectory). Particulars belong in `test/` and `docs/FINDINGS.md`.

- **Dependency versions** (Dymola 2026x, MSL 4.1.0, WSL2 Linux 6.6).
  Historical context; can move; not Mind material.

- **The three-leg comparison table.** Lives in `docs/FINDINGS.md` Headline
  section. The Mind names the LESSON (Rule #8 — wall moves with paradigm);
  the table carries the numbers.

---
**Last distilled:** 2026-05-26 (hand-distilled by the Soul-System Tier 3b
validation arc; deployed despite the project's FROZEN status because the Mind
preserves learned doctrine in compressed form — see witness SOUL-070 + the
Tier 1-style candidate at `docs/experiments/2026-05-26-mind-soultest-modelica-candidate.md`
in the Soul-System repo).
