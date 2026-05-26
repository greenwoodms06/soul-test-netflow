# Findings ledger — MTK capability + Soul System

Running record from the Julia/MTK thermal-chain dogfood. Two audiences:
**MTK-Fn** = ModelingToolkit capability findings (shareable with MTK devs);
**SOUL-Fn** = Soul-System process findings. Each: claim · evidence · note.
All performance numbers measured on one WSL2 box, 2026-05-21; MTK v11.26.5,
MTKStandardLibrary v2.28.0, NonlinearSolve v4.19.1, Julia 1.11.9.

---

## MTK capability findings

**MTK-F1 — Stream connectors work cleanly for 1-D enthalpy advection.** A custom
`FluidPort` (`m_flow` Flow + `h_outflow` Stream) with `instream()` upwind energy
balance conserves energy to machine precision (residual 0.0 W over a 10-cell
channel). *Positive.* (`test/slice2`, `slice3`)

**MTK-F2 — Reproduces a hand-rolled solver to 25 mK.** Porting netflow's exact
nonlinear closures (UO₂ k(T), gap conduction+gray radiation, Zr, Dittus-Boelter)
into MTK matches the re-measured netflow pin to **0.025 K** node-by-node.
*Positive.* (`test/slice4`)

**MTK-F3 — Numeric solve is fast and scales.** With colored sparse AD + KLU, the
nonlinear 2D mesh solves at **0.064 s @ 10k, 0.38 s @ 40k, 1.47 s @ 90k** — matches
/ beats netflow's scipy-sparse-LU (1.7× faster at 10k, parity at 90k), on a
*nonlinear* solve vs netflow's *linear* one. *Positive.* (`bench/scaling_native.jl`)

**MTK-F4 — The scaling bottleneck is `mtkcompile`/codegen, not the numerics.**
Per-component `connect()` emits one **unrolled** residual/Jacobian; `mtkcompile`
scales ~N^1.4–1.7 (≈8 s symbolic + 38 s JIT at only 599 unknowns). **Array variables
do not help** — `mtkcompile` scalarizes array equations (loop-built 0.7→55 s,
array-slice `interior~zeros` 1→160 s over N=1k→20k). So the per-component path does
not reach netflow's 10⁴–10⁵ regime; a hand-written loop residual (or MethodOfLines)
does. *Actionable for devs: codegen scaling on per-component & array-equation models.*
(`bench/scaling_mtk.jl`, `scaling_arraysym.jl`, `scaling_native.jl`)

**MTK-F5 — The high-performance sparse path is not discoverable/default.**
`NonlinearProblem(sys; sparse=true)` builds a *symbolic* sparse Jacobian (slow to
generate + evaluate) and does **not** auto-use coloring or a sparse linear solver.
The fast path needs, explicitly: a cheap sparsity pattern (`TracerSparsityDetector`,
not the symbolic jac), a `colorvec`, and `linsolve=KLUFactorization()`. NonlinearSolve
v4 *removed* `autodiff=AutoSparse(...)` for nonlinear problems (its error message does
point to `sparsity`/`jac_prototype`/`colorvec`). *Friction: a user following the
obvious path gets the slow one.* (`bench/diag_*.jl`)

**MTK-F7 — Cross-domain composition works cleanly (the headline strength).** A
custom **signal-domain** point-kinetics component (`RealInput` fuel-T → `RealOutput`
power, 1 delayed group + Doppler) wired to the **thermal acausal domain** (HeatPort:
PrescribedHeatFlow ← power, HeatCapacitor, R, FixedTemperature, TemperatureSensor →
feedback) via MTKStandardLibrary `Blocks`. The coupled nonlinear feedback loop
solved and hit the **analytic Doppler equilibrium exactly** (ρ→0, T to <0.05 K;
correct prompt-jump + settling, `results/neutronics_feedback.png`). Build was
**friction-free** — components from three areas (custom Block, Blocks, Thermal)
composed as expected. *Positive — validates MTK's multiphysics-composition claim.*
(`test/slice7`)

**MTK-F10 — Added 2D coupling (axial conduction) composes cleanly.** Coupling
adjacent fuel centerlines with `ThermalConductor`s (radial→2D conduction field,
wider Jacobian band) solves cleanly with **energy conserved to ~1e-9 W** for all
conductances; the centerline peak smooths as G_ax↑ (1371→1294 K) as expected, and
realistic UO₂ axial conductance (4.3e-4 W/K vs radial ~10 W/K) is correctly
**negligible**. *Positive — structural coupling handled.* (`test/slice10`)

**MTK-F11 — Gotcha: a `G=0` `ThermalConductor` makes the solve `Unstable`.** A
degenerate zero-conductance element (used to represent "no coupling") yields a
singular/unstable system; the fix is to omit the element, not set G=0. *Minor
trap, easy to hit when parametrizing coupling on/off.* (`test/slice10`)

**MTK-F9 — Assembly: small is fine, full-core per-component is compile-bound.** On
the *realistic* coupled model (parallel fuel-channels, prescribed flow), the solve
stays cheap but per-component `mtkcompile` **superlinear and steepening**: 25-pin
(499 unknowns) 7.3 s; 49-pin (979) 18.8 s; 100-pin (1999) **71.1 s** — local
exponent ~N^1.6 at the large end (warm solve still only 0.09 s at 2000 unknowns).
Extrapolated from this anchored curve, a full 17×17×30 assembly (~17k unknowns) is
**~25–40 min of `mtkcompile`** — impractical per-component, feasible via the loop
path (MTK-F3). *(Note: an earlier ~10 min estimate extrapolated from 499 unknowns
was ~3–4× optimistic; the exponent steepens — measured to 2000 to correct it.)* So
"push to full assembly" per-component is blocked by MTK-F4's codegen wall, not the
solver. (`bench/scaling_assembly.jl`)

**MTK-F8 — Momentum/hydraulic network solves, incl. the zero-flow singularity.**
Parallel channels with friction Δp = K·ṁ|ṁ| (across/through p/ṁ) split flow to
**machine precision** (ṁ_i = √(Δp/K_i)). The genuinely-hard case netflow flagged —
starting at ṁ=0, where the friction Jacobian `2K|ṁ|` is singular: **bare
`NewtonRaphson` gets trapped** (stays at ṁ=0), but MTK's **default polyalgorithm
escapes it** and finds the solution (Δ 1.7e-10). *Positive (robust default handles
what netflow special-cased), with a caveat: pick the robust solver, not bare Newton,
near singular nonlinearities.* Also: retcode read `Stalled` on a converged solve —
another misleading-retcode instance (cf. MTK-F6). (`test/slice8`)

**MTK-F6 — Small API/UX friction points (each cost a debug cycle).**
`@mtkmodel` did not resolve in `Main` (lives in the `SciCompDSL` sublib) → used the
functional `System(eqs,t,vars,ps; name, systems=[...])` form; `HeatCapacitor` takes
`T`, not `T_start`; large-magnitude enthalpy (h~1.6e6) makes a *converged* solve
report `retcode=MaxIters` unless `abstol` is loosened to physical scale; transient
DAE initialization throws a cryptic error until `OrdinaryDiffEqNonlinearSolve` is
explicitly loaded.

---

**MTK-F12 — The compile wall is ECOSYSTEM-WIDE (scalarizing codegen), and the
shipping escape is GATED.** Investigated the two "you should've done X" rebuttals
directly; both confirm the wall rather than escape it:
- **Array equations scalarize** (not user error). A single array equation
  `interior ~ zeros(N-2)` on `@variables u(t)[1:N]` compiles to **N scalar
  equations** (unknowns = N-2, not O(1)); compile grows with N
  (`bench/repro_array_scalarize.jl`). MTK's own roadmap confirms vectorized
  array-equation codegen is a **goal, not shipped** ("we aim to allow simplification
  without requiring scalarization" + Reactant.jl, future tense — JuliaHub blog
  2025-09-20). Auto-scalarization was *removed* in v9, but that ≠ looped codegen.
- **MethodOfLines has the SAME wall** (measured): 2D heat, discretize+1st-solve =
  0.7+1.1 s @ 81 pts → **16.5+45.6 s @ 1521 pts**, ~N^1.3 (`bench/scaling_mol.jl`).
  Matches SciML lead Rackauckas on record: *"MethodOfLines uses a scalarization
  which leads to long compile times"* (Discourse; community ~6000 s @ 10⁴ pts). So
  the recommended PDE tool does **not** escape the wall.
- **The only shipping fix is `JuliaSimCompiler.jl`** (IRSystem backend, IR linear in
  op count) — and it is **not in the General registry** ("not found … in registry");
  it requires the JuliaHub registry + license (free non-commercial, paid commercial).
  ⇒ *Access-escalation (for the Body): testing the real escape needs a JuliaHub
  account.* This ties the scaling story to the JuliaSim/Dyad commercial layer.

*Net: the wall is real, acknowledged by SciML, spans per-component + array-equations
+ MethodOfLines, and the documented escape is gated. This is a mapped result, not a
"used it wrong" — the obvious rebuttals were checked and measured.* (supersedes the
scattered scaling notes in MTK-F4/F9 — they remain as the per-model measurements)

## Soul System findings

**SOUL-F-a — Completion gate verifies *sourcing*, not *measurement validity*.** The
performance benchmark shipped a Coherent Falsehood ("MTK walls ~5000; netflow wins
on scale") that **passed the completion gate** — because the claim *was* anchored to
measurements; they were just methodologically flawed (linear-elimination artifact +
polluted timing). Only the Body's domain skepticism caught it. *external-anchor ≠
correct-anchor.* **Candidate amendment:** a measurement-sanity / independent-re-run
check for load-bearing benchmark numbers.

**SOUL-F-b — Both expansion & completion gates fired unprompted (positive).** The
expansion gate forced the prior-art sweep *before any code* (no Universe Collapse —
netflow's whole lesson), and the completion gate caught the stale netflow-README
overclaim (1201.9 K) before the Body did, on its first fire.

**SOUL-F-c — In-artifact retraction prevents a standing falsehood.** When the
performance error was found, banner-flagging the wrong section *in the doc* before
the corrected numbers landed kept a known-false claim from standing as fact during
the fix. Cheap, effective discipline.

**SOUL-F-f — Reaching outward BEFORE building overturned the plan (expansion gate
value).** The plan was "try MethodOfLines (the right tool) so the writeup isn't
dismissed as 'you should've used MOL'." An Emissary research pass *first* found MOL
has the **same** scalarization wall (Rackauckas on record) — a Multiverse moment that
inverted the conclusion (the rebuttal itself is wrong) and saved building a model to
"prove" a tool that couldn't have escaped the wall. Reaching out before acting is
the accelerator, not ceremony. (Then verified empirically anyway — research + own
measurement, not one or the other.)

**SOUL-F-e — Verification thresholds must match the physics' slowest mode.** Slice 7
first "FAILED" on a ρ<1e-6 check that was actually the physical **delayed-neutron
tail** (slow mode τ≈12.5 s > thermal 6.3 s) — the model was right, the *check* was
miscalibrated (integration < several × slowest mode). Reinforces SOUL-F-a: a check
can be wrong, not just the work. Equilibrium claims need t ≫ slowest time constant.

**SOUL-F-d — The guardrail (re-measure, don't trust the record) paid for itself
twice.** netflow's README was stale on both the pin temperature (1201.9 vs measured
1204.75 K) and the scaling numbers; trusting either would have anchored a benchmark
to wrong baselines.

---

*Append new findings per slice. Keep claim · evidence · note.*
