# Step 0 — Dymola advanced-flag research + MSL primitive scan

**Date:** 2026-05-26
**Purpose:** Stage the flag set and modeling-choice levers for step 2 (advanced-flag dogfood). Per ADR-0002, MSL only — no third-party libraries.

## Flag set (to dogfood in step 2)

### A. Sparse linear solver (primary lever for the N=5000 CoupledChain wall)

| Flag | Default | Try | What it does |
|---|---|---|---|
| `Advanced.SparseActivate` | `false` | `true` | Activates sparse linear solver inside the algebraic-init Newton loop. Most cited "first thing to try" for large models. |
| `Hidden.SparseSolverType` | (KLU per Dymola convention; public docs scarce) | `"KLU"` then `"Pardiso"` if available | Selects the sparse-LU backend. Pardiso uses BLAS; KLU is the EDA-style circuit solver. |

### B. Code generation / compile (lever for the gcc-cc1 wall at 17×17×30)

| Flag | Default | Try | What it does |
|---|---|---|---|
| `Advanced.ParallelizeCode` | `false` | `true` | OpenMP-parallelizes generated C. Helps sim runtime, not compile time. |
| `Advanced.NumberOfCores` | auto | leave auto | Manual override; not needed. |
| **gcc options** | `-O1` (Dymola convention) | `-O0` for compile-time mitigation | Set via `dsbuild.sh` editing or `gccCompilerOptions`. Halves cc1 cost at price of slower dymosim. |

### C. Integrator (lever for stiffness + DAE handling)

| Method | DAE mode | Notes |
|---|---|---|
| `"Dassl"` | yes | Current default. BDF, robust for stiff DAEs. The bench baseline. |
| `"Cvode"` | yes (BDF) | Sundials BDF; works on large sims where Dassl fails. Dense linear only (paired with our model size, depends on `SparseActivate`). |
| `"Radau"` (RadauIIa) | yes | **LBL Buildings Library recommendation for thermal-fluid systems at 1e-6 tolerance.** Worth trying. |
| `"Esdirk23a"` / `"Esdirk34a"` / `"Esdirk45a"` | yes | Stiff DAE with state events; ESDIRK family. Lower-order Esdirk23a is sometimes fastest for modest tolerance. |

**Tolerance ladder:** 1e-6 (current, LBL recommendation) vs 1e-4 (Dymola factory default).

### D. Modeling-level levers (free with our models, MSL-compliant)

These are NOT advanced flags but `Modelica.Fluid` parameter choices that LBL flags as higher-impact than solver tuning:

- `from_dp=false` for serially connected flow resistances — applies to step 3c subchannel cross-flow.
- `dynamicBalance=true` to remove algebraic loops in cells.
- Use `nominal` attributes on state variables for better Newton init (helps the N=5000 init-solver wall).

## Step-2 dogfood plan (deferred to step 2 execution)

Flag combinations to measure (against existing 17×17×30 baseline = 397.1 s):

1. **Baseline** (Dassl + 1e-6, no Advanced flags) — already measured, 397.1 s.
2. **Sparse only** (`Advanced.SparseActivate=true`) — single lever.
3. **Sparse + Radau** — Sparse + LBL's thermal-fluid recommendation.
4. **Sparse + Cvode** — Sparse + multistep BDF.
5. **Sparse + Esdirk23a** — Sparse + lower-order ESDIRK.
6. **Sparse + Radau + ParallelizeCode** — Sparse + best integrator from above + multi-core.
7. **gcc -O0 + best from (2-6)** — cc1-wall mitigation.

Same matrix on N=5000 CoupledChain (the init-solver wall scenario).

**Verification at each step:** physics still correct via `test/verify_assembly_physics.py` invariants (Q_total = 19.04 MW, T_outlet_max in 600-615 K band, T_centerline_hot matches slice-3 value).

## MSL primitive scan (for step 3 physics breadth, by sub-step)

| Sub-step | Pattern | MSL primitives needed | Already in project? |
|---|---|---|---|
| **3a — Cross-pin axial conduction** | `ThermalConductor` between adjacent FuelPin centerlines, indexed by 17×17 grid neighbor map | `Modelica.Thermal.HeatTransfer.Components.ThermalConductor` (intra-pin axial already uses it in `AxialConductionChain.mo`) | YES — connect()-pattern only |
| **3b — Pin-by-pin neutronics feedback** | Slice-7 `PointKinetics` × 289 + shared power normalization through a signal bus | Existing `Components.PointKinetics` + `Modelica.Blocks.Math.Sum` + `Modelica.Blocks.Routing.Multiplex` | YES — wiring only |
| **3c — Subchannel cross-flow** | Bidirectional fluid connection between adjacent CoolantCells across the channel grid | `Modelica.Fluid.Fittings.SimpleGenericOrifice` (or `StaticPipe` with friction), plus the stream-connector machinery already in CoolantCell | YES — new component + connect() |

**No MSL gaps identified.** All three step-3 sub-steps are MSL connect()-pattern extensions of components already in the project.

## Sources (citation trail for future-me)

- LBL Buildings Library performance guide (radau + 1e-6 thermal-fluid recommendation; modeling-level levers): https://simulationresearch.lbl.gov/modelica/userGuide/performance.html
- Dymola advanced-flag overview (Claytex): https://www.claytex.com/tech-blog/advanced-flag-changes-in-dymola-2025x/ (cert-expired at fetch time, content via WebSearch)
- OpenModelica solver docs (DAE mode, KLU/Pardiso, integrator behavior): https://openmodelica.org/doc/OpenModelicaUsersGuide/latest/solving.html
- Dymola 2025x release-notes mention of sparse-solver activation: https://www.claytex.com/tech-blog/advanced-flag-changes-in-dymola-2025x/

## Things this research did NOT settle (defer to empirical step 2)

- Exact public default of `Hidden.SparseSolverType` (KLU vs Pardiso). Measure empirically.
- Whether `gcc -O0` is settable via a Dymola interface flag or must be done by editing `dsbuild.sh`. Probe at step 2 start.
- Whether Dymola's `Cvode` works with `Advanced.SparseActivate=true` or falls back to dense LAPACK. Measure empirically.
- Whether Radau-IIa is the same as `method="Radau"` or needs a specific spelling (`"Radau3"`, `"RadauIIa3"`). Probe at step 2 start.
