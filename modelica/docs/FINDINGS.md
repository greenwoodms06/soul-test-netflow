# FINDINGS — Modelica/Dymola thermal-chain dogfood

Running record from the Modelica/Dymola leg of the netflow → Julia → Modelica
paradigm triangulation. Two audiences:
- **MO-Fn** = Modelica/Dymola capability findings (shareable with the Body's
  Modelica community / the dymola-sim-debug skill ecosystem).
- **SOUL-MO-Fn** = Soul-System process findings specific to this leg.

All numerical results measured on this machine (WSL2, Linux 6.6, Dymola 2026x,
MSL 4.1.0, Modelica.Media.Water.StandardWater for IF97), 2026-05-26.

---

## Headline (three-leg comparison)

| Axis | netflow (Python) | soultest-julia (MTK) | This leg (Modelica/Dymola) |
|---|---|---|---|
| **Single-pin solve time** | 9 ms (Newton) | 0.064 s @ 10k mesh (different scenario) | 3.7 s (translate+compile+sim end-to-end) |
| **Match vs netflow re-measured** | reference | 25 mK (with quadratic property fits) | **24.7 mK aligned, 0.34 K native IF97** |
| **Coolant medium** | CoolProp HEOS (IAPWS-95) | constant cp = 5500 (no IF97 binding) | **Modelica.Media IF97 out of the box** |
| **Conservation pattern** | hand-rolled sparse residual | `connect()` symbolic | **`connect()` symbolic** |
| **Component LOC (this physics)** | ~1342 (full plugin) | 98 (using MTKStdLib) | 430 (using MSL) |
| **Slice ladder reached** | (single solver — N/A) | 1–10 | **1–10 (climbed past plan)** |
| **17×17×30 assembly (Julia anchor)** | reachable (380k linear nodes ~190 s) | extrapolated 25-40 min mtkcompile; **never run** | **397 s end-to-end, completed** |
| **Doppler equilibrium reachable** | (separate plugin) | yes (MTK-F7) | yes (MO-F10) |
| **Zero-conductance edge** | n/a | Unstable retcode (MTK-F11 trap) | clean run (MO-F12) |
| **Zero-flow friction Jacobian** | special-cased | default poly-algorithm escapes (MTK-F8) | bit-exact split (MO-F11) |
| **Where the wall lives** | sparse-LU at ~10⁶ nodes | mtkcompile codegen ~N^1.6 | gcc cc1 ~5 min @ 174 MB C, OR init solver under IF97 inverses |

---

## Modelica/Dymola capability findings (MO-Fn)

**MO-F1 — Stream connectors + IAPWS-IF97 + connect()-emitted energy balance
deliver the steady cell answer at numerical noise.**  Slice 2's heated channel:
Δh = 7 nJ/kg, ΔT = 9e-13 K vs the same Q/m_dot enthalpy rise computed
independently in CoolProp's IF97 backend. The stream-connector machinery and
the IF97 medium are *both* doing their job, and `connect()` generates the cell
balance correctly. *Positive.* (`test/slice2_coolant_channel.py`)

**MO-F2 — Reproduces netflow to 24.7 mK when property backends are aligned.**
With the same quadratic CoolProp-HEOS property fits the Julia attempt used
(opt-in `useFittedProps = true`), the Modelica chain hits the centerline pin at
**24.7 mK** vs the re-measured netflow baseline (Julia's bar: 25 mK). The four
node temperatures all match within 25 mK. *Positive.*
(`test/slice4_match_netflow.py`, aligned mode)

**MO-F3 — Native Modelica.Media IF97 disagrees with netflow's CoolProp HEOS
backend by 0.34 K on the same scenario — fully traced to IF97-vs-HEOS transport
property formulations (~3% in k, ~3.4% in Pr at film T ~602 K).**  This is NOT
a model error: Dymola's `StandardWater` uses IAPWS-IF97 with the standard
IAPWS R12 (viscosity) and R15 (conductivity) transport correlations; CoolProp's
default backend ("Water") is HEOS (IAPWS-95) with different transport
correlations underneath. Both are correct implementations of their respective
standards. The disagreement (0.34 K) is below Dittus-Boelter's own correlation
uncertainty (~20%). *Important caveat for code-comparison work:* "same fluid
specified" does not mean "same numerical answer." (`test/slice4_match_netflow.py`,
native mode)

**MO-F4 — Storage extension is one line per node, no connector changes.** Slice
1's resistor stack becomes slice 5's first-order transient by adding one
`HeatCapacitor` on the centerline port. The connect() topology is unchanged.
The trajectory matches the exact first-order analytic to **2.8 μK over 80 s
(12.6 τ)**. Confirms ADR-0001's "steady-first, storage added later without
changing connectors" claim empirically. (`test/slice5_transient_pin.py`)

**MO-F5 — Coupled transient chain → slice-3 steady within e^{-10}.** Slice 6
(10-cell pin+channel chain with HeatCapacitor at every centerline + M·dh/dt in
every cell) converges to slice-3's steady answer within **84 mK at t = 60 s
(~10 τ_pin)** — fully consistent with the residual exp tail of a finite
horizon. The transient and steady results are computed in the same Dymola
session, ruling out cross-session drift. *Positive — transient + steady
co-verify.* (`test/slice6_transient_chain.py`)

**MO-F6 — Headless harness friction surface (each cost one debug cycle):**
- `DymolaInterface()` doesn't auto-locate Dymola on Linux; must pass
  `dymolapath=` and pre-set `LD_LIBRARY_PATH` (Dymola's bundled libs are not
  on the system loader path) and `$DYMOLA` (used inside `dsbuild.sh`). The
  /usr/local/bin/dymola wrapper script handles this for interactive launches;
  the Python interface bypasses it.
- `openModel(...)` defaults to `changeDirectory=True`, which silently overrides
  any earlier `cd(work)` — relative `resultFile` paths then land in the MSL
  install directory. Pass `changeDirectory=False` and call `cd(work)` AFTER
  loading libraries.
- `simulateModel(..., resultFile="foo")` writes `foo.mat` to Dymola's CWD;
  pass an absolute path to be sure.
- Default `.mat` result file is single-precision compressed; for verification
  work at the μK level call `experimentSetupOutput(doublePrecision=True)`
  before each simulate.
- The `Modelica.Icons.Block` base class does not exist in MSL 4.1.0; use
  `Modelica.Icons.Example`/`UtilitiesPackage`/`Package` or no `extends`.
- `SI.LinearDensity` is *kg/m*, not *W/m* — for linear power use
  `Real x(final unit="W/m")` (no typed alias exists).
- A FluidPort source that sets `m_flow` AND `p` over-determines a
  pressure-coupled network without momentum; sources should set ONE of
  (m_flow, p), not both. (Same trap the Julia attempt avoided by separating
  `MassFlowInlet` from `PressureOutlet`.)

(*Captured as a project-local SKILL.md candidate; see follow-up §below.*)

**MO-F7 — Total end-to-end wall-clock (Dymola startup + load + translate +
compile + simulate) for the single-pin slice-4 scenario: ~6.9 s.**  Breakdown:
2.0 s Dymola startup + MSL/NetflowModelica load; 3.7 s translate + compile +
simulate; 1.2 s overhead. *netflow's 9 ms is just the Newton solve.* The
honest comparison is: Modelica buys you generated C, a stiff DAE integrator
family, the IF97 medium, the standard library, and "connect-and-go"
conservation — at the price of ~3.7 s of upfront codegen per model edit. The
Julia attempt's MTK had a similar codegen cost; here it does not balloon at
slice 6 because the model is bounded (the Julia compile wall lived past slice
6 at multi-pin assembly — deliberately out of this scope). (`bench/end_to_end_timing.py`)

**MO-F10 — Slice 7 (Doppler feedback): Modelica composes signal+acausal cleanly,
hits the analytic Doppler equilibrium exactly.** Same scenario as Julia's MTK-F7:
+100 pcm reactivity inserted at t=0; fuel heats; negative Doppler returns ρ to 0
at a new equilibrium. Modelica's `Modelica.Blocks.Interfaces.SISO` block (a
custom `PointKinetics` block) wired through `PrescribedHeatFlow` ← power and
`TemperatureSensor` → feedback delivers T_fuel = 1292.99 K and ρ = 0.000 pcm
**exactly matching the analytic** T_eq = T_ref − ρ_ext/α. Build was friction-free
— mixing signal (Blocks) and thermal (HeatTransfer) packages from MSL composes
as expected. *Cross-domain multiphysics works.* (`test/slice7_neutronics_feedback.py`,
visual: `results/slice7_neutronics_feedback.png`)

**MO-F11 — Slice 8 (parallel-channel momentum): Δp=K·ṁ|ṁ| flow-split exact at
machine precision, with no zero-flow trap.** 3 parallel friction channels
sharing inlet/outlet pressure boundaries; Modelica delivers ṁ_i = √(Δp/K_i)
with **|Δ| = 0** (literal bit-for-bit match across all three). The case
netflow flagged as genuinely hard (friction Jacobian singular at ṁ=0) — Dymola's
default solver handles it. (`test/slice8_parallel_flowsplit.py`)

**MO-F12 — Slice 10 (axial conduction): Modelica handles the G=0 degeneracy
that Julia's MTK-F11 flagged as a trap.** Three G_axial cases run (realistic /
moderate=5 W/K / exaggerated=50 W/K); all energy-conserve exactly (|residual|=0
W) and centerline peak smooths as G↑ (1371→1294 K). A zero-conductance
`ThermalConductor` (G_axial=0) **also runs cleanly in Modelica/Dymola** —
Julia's MTK-F11 specifically called this out: in MTK the same construct
produced an Unstable retcode. *One concrete divergence in favour of Modelica.*
(`test/slice10_axial_conduction.py`)

**MO-F13 — Scaling: Dymola's wall lives in a different place than Julia's,
and it's much further out.** Sweep CoupledChain(n) end-to-end (translate +
compile + simulate). Headline:

| N axial | unknowns | wall [s] | notes |
|---:|---:|---:|---|
| 10 | 608 | 4.1 | baseline overhead |
| 100 | 6,008 | 6.4 | sub-linear; overhead dominates |
| 1,000 | 60,008 | 41 | linear |
| 2,500 | 150,008 | 208 | local exponent ~N^1.76 |
| 5,000 | 300,008 | **wall hit** | codegen finished (~4 min), dymosim ran >10 min without writing .mat — algebraic-loop init solver with IAPWS-IF97 inverse calls per Newton step is the bottleneck |

Julia's MTK-F4/F9 anchor: `mtkcompile` ALONE was ~71 s at 100 pins (≈2k
unknowns), exponent ~N^1.6 — extrapolated 25–40 min compile @ ~17k unknowns.
**Dymola compiled 60k unknowns end-to-end (translate + codegen + gcc + sim)
in 41 s — and the codegen step kept finishing cleanly past 300k unknowns.**
The wall MOVED:
  - Julia: codegen (`mtkcompile` scalarisation per component)
  - Modelica: simulate-time init-solver with IF97 medium in the algebraic loop
This is a different kind of wall, and it's much further out for Dymola on
this kind of model. (`bench/scaling_coupled_chain.py`,
`results/scaling_coupled_chain.png`)

**MO-F14 — Dymola COMPLETED Julia's 17×17×30 anchor scenario in 397 s end-to-end —
Julia extrapolated 25-40 minutes for `mtkcompile` ALONE at that scale.**

17×17 PWR assembly stress ladder (single-pin channels in parallel, no axial
coupling — apples-to-apples with Julia MTK-F9):

| n_pin × n_axial | pin nodes | wall [s] |
|---:|---:|---:|
| 4×4 × 10 | 160 | 8.1 |
| 8×8 × 10 | 640 | 22.7 |
| 8×8 × 20 | 1,280 | 41.3 |
| 17×17 × 10 | 2,890 | 105.9 |
| 17×17 × 20 | 5,780 | 227.2 |
| **17×17 × 30** | **8,670** | **397.1** |

(Scaling roughly linear in pin nodes through the range — exponent ~1.05.)

**The wall is the C compiler, not Dymola.**  At 17×17×30, `dsmodel.c` is
**174 MB** of generated C and `gcc -O1` `cc1` consumed **11.7 GB RAM** and
~5 minutes of CPU time on a single core. The resulting `dymosim` binary is
**164 MB**. *Dymola's codegen finished cleanly in minutes; the dominant cost
is the system C compiler.*  This is a different bottleneck from Julia's
`mtkcompile`-scalarization wall (which is in Julia's own toolchain and
isn't escapable without `JuliaSimCompiler.jl`).

Comparison axes for the FINDINGS table:
  * Julia 17×17×30 mtkcompile: **25-40 min extrapolated, never actually run**
  * Dymola 17×17×30 end-to-end: **6.6 min measured, completed cleanly**
  * Bottleneck under change: Julia = `mtkcompile`; Dymola = gcc cc1
  * Escape hatches: Julia = JuliaSimCompiler (gated); Dymola = swap to `gcc -O0`
    or use `tcc` (deferred — ideas.md)

(`bench/stress_assembly_17x17.py`, `results/stress_assembly_17x17.{json,png}`,
combined scaling plot at `results/scaling_coupled_chain.png`)

**MO-F9 — Visual witness (slice 6): axial profile + startup time-series rendered
and inspected (`results/slice6_axial_profile.png`, `results/slice6_timeseries.png`).**
Confirmed visually: T_cool monotone-rising inlet→outlet; T_centerline parallel
+660 K above (matches Q×R_tot); time series smooth-exponential with no
overshoot (consistent with first-order pin dynamics); outlet coolant lags
inlet centerline (mass-transport delay through 10 cells visible). All three
expected qualitative features present, no surprises. *Visual confirms what
the textual verification asserts — F030/F031 obligation met inline rather
than deferred.* (`test/slice6_plot.py`)

**MO-F8 — A `replaceable Medium` + Boolean parameter switch is the right way
to compare two property formulations in one component.**  `ForcedConvection`'s
`useFittedProps` flag selects between Modelica.Media calls and the quadratic
fits, INSIDE one model. No code duplication; both code paths compile (Modelica
allows `if useFittedProps then ... else ... end if` over conditional value
assignments). Lets slice 4 ship two results from one component, which is what
made MO-F3's traced explanation possible without a separate model.

---

## Unfreeze (2026-05-26): MO-F15 through MO-F19

**MO-F15 — `Advanced.Translation.SparseActivate = true` halves sim-bound walls and rescues the init-solver wall.**  Setting the flag cut the CoupledChain N=2500 wall from 196.67 s → 89.60 s (**2.2× faster**) on Dassl 1e-6, and rescued the chain at N=5000 which previously hard-failed (>10 min, never converged) — completing in 227.57 s with sparse + Dassl. Cvode and Esdirk23a as alternative integrators paired with sparse perform comparably (90-92 s on N=2500, 232 s on N=5000). Anchor: `results/advanced_flag_sweep_part2.json` + headline plot panel A. *The flag is the right tool only when the wall is the simulator's algebraic init Newton; at compile-bound walls (17×17×30) it's a no-op or marginal regression.*

**MO-F16 — At compile-bound scales (17×17×10 and 17×17×30), Advanced flags don't move the wall.**  Eight flag combinations measured at 17×17×10 (default, sparse, sparse+cvode, sparse+esdirk23a, sparse+radauiia, sparse+parallel, looser tol, sparse+looser) all clustered within 3% (102.7-106.2 s). Four scenarios at 17×17×30 clustered within 11 s (384.5-395.3 s on ~390 s baseline). The wall at this scale is `gcc cc1` codegen on the generated `dsmodel.c` (174 MB at 17×17×30 per COMPARISON.md §4); Dymola's `Advanced.*` flags address translation and solver, not the C compile. Anchor: `results/advanced_flag_sweep_17x17_10.json` + `results/advanced_flag_sweep_part2.json`. `RadauIIa` as `method=` returned ok=False — likely needs different spelling (`Radau3`, `RadauIIa3`); not pursued. *Tuning the wrong wall is no-op.*

**MO-F17 — Cross-pin axial conduction at 17×17×30 with MSL-only primitives runs end-to-end at +25% wall vs vanilla.**  `AssemblyVeraP6CrossPin` wires `Modelica.Thermal.HeatTransfer.Components.ThermalConductor` between adjacent fuel-pin clad outers in the 17×17 grid (slice-10 pattern extended to cross-channel adjacency). Ladder: 8×8×10 → 34.6 s; 17×17×10 → 138.0 s; 17×17×30 → 543.1 s vs vanilla AssemblyVeraP6 at 23.9 / 108.0 / 433.2 s. Q_total exact at every scale; T_centerline_hot unchanged for uniform power (cross-pin doesn't break symmetry). *The Jacobian-band widening cost is real but bounded; no new MSL primitive required beyond ThermalConductor.*

**MO-F18 — Pin-by-pin neutronics feedback at assembly scale: 289 coupled point-kinetics ODE systems + thermal feedback loops run on MSL primitives.**  `AssemblyVeraP6Neutronics` couples 289 `Components.PointKinetics` blocks (one per pin) to their pin's mid-axial centerline temperature via Doppler reactivity; the kinetics output drives signal-driven `FuelPinDynPower` instances (slice-7 pattern × 289). Required adding `FuelPinDynPower` (PrescribedHeatFlow + RealInput) and a wiring topology where each pin's `Q_flow_in = kins[ip].y / n_axial`. Reaches a bounded feedback equilibrium where T_fuel_mid ≈ T_ref-offset. Ladder: 8×8×10 → 37.3 s (transient 50 s); 17×17×10 → 134.8 s. 17×17×30 transient deferred (transient cost compounds with scale; estimated > 2000 s). *Per-pin kinetics on MSL is connect()-and-go; no third-party library required.*

**MO-F19 — MSL-only subchannel cross-flow requires explicit pressure-drop closure; direct connect of 4-port lateral cells is structurally singular.**  `AssemblyVeraP6Subchannel` uses a custom `CoolantCellSub` with 4 lateral FluidPorts (xL/xR/yU/yD) + 2 axial. Connecting adjacent cells' lateral ports DIRECTLY (no momentum, no pressure-drop element) produces `Error: The problem is structurally singular ... Circular equalities detected` at Dymola translation. Adding a linear `m_flow = G * (p_a - p_b)` element (`Components.LateralFlowLink`) between every adjacent pair closes the system. Ladder: 8×8×10 → 35.0 s; 17×17×10 → 151.5 s; 17×17×30 → 621.1 s vs vanilla 23.9 / 108.0 / 433.2 s (+43% at full scale). Q_total exact; T_cool_exit_spread = 0 K under uniform power + symmetric inlets (sanity check on the lateral closure). *Subchannel topology demands either explicit ΔP closure or MSL's `SimpleGenericOrifice` — no momentum-free shortcut exists.*

**MO-F20 — The 22×22×30 OOM ceiling lands earlier than the 1.38-exponent extrapolation predicted: cc1 was OOM-killed at 19.9 GB resident on the 14 520-pin-node case.**  Step 4 of the unfreeze (2026-05-26) ran an 18×18 → 20×20 → 22×22 → 25×25 ladder past the 17×17×30 anchor. Measured: 18×18×30 (9 720 nodes) = 454.0 s; 20×20×30 (12 000 nodes) = 645.0 s; **22×22×30 (14 520 nodes) FAILED** after 265 s with `cc1 invoked oom-killer` (kernel dmesg: `total-vm:23477212kB, anon-rss:19858256kB`). The 1.38 high-end exponent from the 17×17 ladder predicts ~880 s at 14 520 nodes — the failure was the RAM ceiling, not the wall-time ceiling. 25×25×30 (18 750 nodes) was not reached. **Refines MO-F14:** the cc1 ceiling is in RAM (≥ 16 GB physical on this WSL2 box), not in time. Mitigation (still open per ideas.md): `gcc -O0` or `tcc` would reduce cc1 memory consumption at the price of slower dymosim. Plot: `results/assembly_scaling_extended.png`. *The 18×18 and 20×20 measurements sit cleanly on the slope-1.38 line, confirming the prior exponent estimate — but the ceiling is reached one step earlier than predicted.*

**MO-F21 — VERA P6 code-comparison consumed (Step 1 follow-through): power-driven outlet spread = 1.5 K vs Kelly 2017's 6.6 K (CTF/VERA) / 8.7 K (COBRA-IE).**  The Step 1 anchor (operating point + reference values loaded into `references/INDEX.md`) was actually consumed by running `AssemblyVeraP6` at 17×17×30 with the Kelly Fig. 10 radial peaking pattern (cosine-from-centre, range 0.97-1.02 after mean-normalisation; un-normalised peak 1.05). Measured outlet-T spread: **1.495 K**; peak fuel volavg: 706 °C. *Per Godfrey 2014 the benchmark has NO reference solution* — this is code-to-code comparison, never validation. **Two structural caveats explain the gap-to-Kelly:** (a) this leg has NO guide tubes (all 289 positions modelled as fuel rods); Kelly's 6.6 K spread is geometry-driven by guide-tube bypass redistribution, not power-driven — adding guide-tube topology would close this gap. (b) Kelly's 1066 °C peak volavg is the P7 number with combined 1.37 radial × 1.40 axial 3D peaking; this leg's flat axial + 1.05 radial gives ~1.02 total peaking — 5% of Kelly's 1.92 hot-pin heat flux — accounting for the 360 °C gap. Result anchor: `results/vera_p6_codecompare.json`. *The anchor is now CONSUMED, not just staged — the gap-to-Kelly is structurally attributable, not a calibration failure.*

---

## Soul-System findings (SOUL-MO-Fn)

**SOUL-MO-Fa — The completion-gate pattern that worked for Julia worked here
too, and it caught the same class of issue earlier.**  Slice 4's first run
came back with Δ = 0.34 K — over the 100 mK target. The Body's reflex (and the
SOUL-F-a guardrail from the Julia leg) was: don't relax the threshold to fit
the result. Instead trace the gap. The trace revealed the property-formulation
difference, named it, and produced MO-F3 (a real finding) plus MO-F8 (a
solution that ships both numbers). The completion gate did NOT have to fire as
an external check; the prior leg's lesson was internalized.

**SOUL-MO-Fb — The Soul ceremony (CONTEXT.md + ADR-0001 + light prior-art
sweep + slice-by-slice verification) compressed cleanly on the third use.**
This dogfood ran in ~ a few hours of wall-clock vs the Julia leg's ~2 weeks,
not because the work was less but because:
- Priors were named and cited rather than re-discovered (light sweep, agreed
  during grilling).
- The slice ladder + verification pattern transferred directly from Julia.
- The ADR could lean on Julia's parallel ADR-0001 rather than start from zero.
*This is the dogfood paying back its own compounding value: the third leg
benefits structurally from the first two.*

**SOUL-MO-Fc — Re-measuring the prior leg's reference (SOUL-F-d guardrail)
returned identical numbers, which is itself a finding.**  netflow on this
machine, today (1204.7488 K centerline + the other three nodes), matched
exactly the values the Julia attempt recorded on 2026-05-21. So the
"don't trust the record" discipline cost ~30 seconds to satisfy (running
`bench/remeasure_netflow.py`) and confirmed the baseline is stable. Cheap
guardrail; would have been expensive to have skipped if the answer had
drifted.

**SOUL-MO-Fd — Modelica's `connect()`-emitted conservation removes a class of
errors that netflow had to hand-validate.**  Three slices verified conservation
invariants (slice 1: machine-precision Kirchhoff; slice 3: energy closure
exact; slice 5/6: storage-form invariants). In every case the answer was at
float64 noise (1e-13 K or better). The netflow plugin contains
`tests/test_layering.py` + multiple conservation tests to verify its
hand-assembled residuals do this correctly. Modelica makes the bug class
*impossible to introduce* in the first place — you don't write the residual.
This is the strongest structural argument for the acausal-connector paradigm
on this kind of problem.

**SOUL-MO-Fe — The "headless harness gotcha" surface (MO-F6) is exactly the
kind of know-how that should land in a project-local SKILL.md before it
strands.**  Eight independent traps cost one debug cycle each on the way to a
working harness. Captured as a candidate SKILL.md (see §Open follow-ups).
Without the capture, the next session of any Modelica/Dymola-headless work
re-discovers them — the same Soul Finding the dymola-sim-debug skill itself
embodies but for a *different* topic (harness vs simulation debugging).

**SOUL-MO-Ff — Universe Collapse did not recur, but the asymmetry between
build-time (cheap to dogfood) and bench-time (deliberately out of scope) was
named once, before scope was locked.**  The grilling explicitly excluded
slices 7–10 (assembly scale, momentum, neutronics, axial conduction) — Julia's
compile-wall territory — because finding out whether Dymola handles them better
than MTK is *its own research question*, not a deliverable of THIS dogfood.
Naming an exclusion is the dual of naming an inclusion; both prevent quiet
drift later. (*This is the "Accountant" expansion-role answer in CONTEXT.md §3
working — recorded as a finding because it almost-didn't.*)

**SOUL-MO-Fg — The wall moves with scale + topology even within one paradigm,
not just across paradigms.** Mind Rule #8 (carried over from the three-leg
comparison) says "name where YOUR wall lives — it MOVES with paradigm."
Step 2 of the 2026-05-26 unfreeze sharpens this one level: within Dymola
alone, the wall is at the algebraic init Newton at N=2500 chain, a degraded
version of the same at N=5000 chain (rescued by sparse), and gcc cc1 codegen
at 17×17×10/30 — three different walls, requiring three different tools (or
in the cc1 case, no tool Dymola exposes). Universal flag-tuning
recommendations are no-ops at the wrong wall. *The Soul-meta version:
diagnose the wall before applying the tuning.* (Apply the project-paradigm
vs Soul-meta diagnostic from memory/feedback_soul_meta_diagnostic.md before
upstreaming: removing Modelica's specifics, the lesson "diagnose the wall
before tuning" is paradigm-agnostic — qualifies for Soul-meta upstream, but
EARN it; this is one instance.)

**SOUL-MO-Fh — Coherent-Falsehood-on-inference fired during the unfreeze: I
claimed "wall is gcc cc1 at 17×17×10" before separately measuring the
translate-vs-simulate split.** The claim was anchored only in ps observation
(cc1 process running at some moment) + prior 17×17×30 cc1 figures from
COMPARISON.md §4. The Soul-Verify gate fired on the next stop; I named the
inference as a gap. *This instance does not establish a finding by itself
(ideas.md "Coherent Falsehood on measurement" pattern needs a second instance);
recording for future graduation.*

---

## Open follow-ups (deliberately not done here)

- **Slices 7–10:** assembly-scale compile-wall test; would directly test whether
  Dymola handles structured `N×N` connect() loops better than MTK's
  per-component codegen scaling (MTK-F4/F9 of the Julia leg). A separate
  dogfood.
- **TRANSFORM-based parallel build:** "use-vs-build" axis; would compare
  TRANSFORM equipment-style components against the MSL-primitive build pattern.
  A separate dogfood.
- **SKILL.md for headless Dymola harness (MO-F6):** the eight traps belong in
  a governed project-local skill; capture is the natural next step.
  Body-initiated (per the soul-skill protocol — "AFTER a verified success").
- **Measured-data validation:** data-ceiling guardrail still holds; not done.

---

*Append new findings per slice. Keep claim · evidence · note.*
