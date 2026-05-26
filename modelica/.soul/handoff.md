# Handoff cursor — 2026-05-26 (afternoon)

**NEXT-SESSION FOCUS:** Body decides; see `docs/COMPARISON.md` §9 ranked
candidates. Most natural next move: advanced-flag dogfood (its own bounded
experiment).

**WHERE WE ARE:** Slices 1–10 + 17×17×30 PWR assembly all PASS on this
machine. Two distinct Dymola walls characterised (gcc cc1 on 174 MB
generated C *or* init-solver-under-IF97 inverses). COMPARISON.md is the
cross-leg artifact. Four Soul-meta findings upstreamed (SOUL-F032..F035).
6 commits on `main`. The three-leg triangulation (netflow / soultest-julia
/ this) is complete and frozen as a finished comparison.

**LIVE AL:** none open (ADR-0001 still governs; no abstraction shift).

**OPEN GATES:** none mid-evaluation. Last `/soul-verify` cleared after the
exponent-trajectory correction (commit `ca1bfb4`).

**NEXT STEP:** Body's choice. The handoff is a stable cursor — nothing is
mid-flight. If resuming for the advanced-flag dogfood, open
`docs/COMPARISON.md` §6 (caveats) and §9 (next-question candidates) first.

## POINTERS (reference, do not duplicate)

- **Cross-leg artifact:** `docs/COMPARISON.md` — three-leg table, both
  scaling stories, three walls characterised, defaults-only caveat, ranked
  next-question candidates.
- **In-leg findings ledger:** `docs/FINDINGS.md` — 14 MO-Fn + 6 SOUL-MO-Fn.
- **Closing finding:** `CLOSEOUT.md` — what was met / new / left open.
- **Abstraction-layer ADR:** `docs/adr/0001-abstraction-layer-msl-heatport-streamfluidport.md`.
- **Frame:** `CONTEXT.md` (§5 lists exclusions; many now moved to "done"
  by the later push, but the doc is left as-written — the deferral
  decisions held at scope-lock time, just got reversed deliberately later).
- **Ideas inbox:** `ideas.md` — 5 forward items + 2 soul-meta observations
  not yet graduated.
- **Upstreamed findings (3 of 4):** `/mnt/d/Projects/Soul-System/findings/open/`
  SOUL-F032, SOUL-F034, SOUL-F035. **SOUL-F033 was reverted by the Body**
  (Soul-System repo commit `6d8562c`) as "project-paradigm, not Soul-meta" —
  Modelica's connect() pattern is project content with Soul-shaped form. The
  source stays at this repo's `docs/FINDINGS.md` MO-F1 / MO-F4 / MO-F10..F12.
  The Body added a diagnostic test to the seed: *"if you removed the project's
  domain entirely, would the lesson still be a Soul System lesson?"* Apply
  this BEFORE upstreaming any future findings from this leg.
- **Bench artifacts:**
  - `bench/remeasure_netflow.py` (SOUL-F-d guardrail)
  - `bench/scaling_coupled_chain.py` (linear-topology N sweep)
  - `bench/stress_assembly_17x17.py` (the assembly ladder)
  - `bench/end_to_end_timing.py`
  - `bench/plot_*.py` (rendering scripts)
- **Slice tests:** `test/slice{1..10}_*.py` + `test/verify_assembly_physics.py`.
- **Visual witnesses:** `results/slice6_axial_profile.png`,
  `results/slice6_timeseries.png`, `results/slice7_neutronics_feedback.png`,
  `results/scaling_coupled_chain.png`, `results/stress_assembly_17x17.png`.
- **Tasks:** all closed (Task #1–15).
- **Git log:** `bf4e407`→`bf5e676`→`47ea1d3`→`dc8b33e`→`22a47e6`→`ca1bfb4`→`d3c2363` on `main` (+ this turn's handoff fix).

## How to reproduce on a fresh session

```bash
# from /home/fig/soultest-modelica
.venv/bin/python bench/remeasure_netflow.py        # confirm netflow baseline still 1204.75 K
for s in 1 2 3 4 5 6; do
  .venv/bin/python test/slice${s}_*.py
done
.venv/bin/python test/slice7_neutronics_feedback.py
.venv/bin/python test/slice8_parallel_flowsplit.py
.venv/bin/python test/slice10_axial_conduction.py
.venv/bin/python test/verify_assembly_physics.py    # 17×17×10 physics check (~106 s)
# Long-running (~7 min): full 17x17x30 + scaling sweep
PYTHONPATH=test .venv/bin/python bench/stress_assembly_17x17.py
PYTHONPATH=test .venv/bin/python bench/scaling_coupled_chain.py
```

## SUGGESTED ROLES / SKILLS for the next session

- **Architect** for the advanced-flag dogfood (it's an *experiment design*
  question — which knobs, which order, what hypothesis per knob).
- **Skeptic** if pushing toward 25×25 or 33×33 assemblies — the 1.38 local
  exponent prediction is the kind of extrapolation Julia's MTK-F9 also got
  wrong (was ~3× optimistic; needed measurement to correct).
- **Artificer** if the headless-Dymola gotchas (MO-F6) get captured as
  `SKILL.md` — see `soul-skill` protocol.
- **Skills:** `dymola-sim-debug` if simulate-side walls become the focus;
  `grill-me` before locking the advanced-flag experiment scope;
  `/soul-expand` if scope materially shifts (e.g. OpenModelica leg).
