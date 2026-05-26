# Three-leg paradigm triangulation — netflow (Python) · soultest-julia (MTK) · soultest-modelica (Dymola)

**Written:** 2026-05-26
**Scope:** one bounded thermal-fluid physics chain (fuel pin → coolant → loop)
solved in three paradigms, on one machine, by one Body, under one
methodology (the Soul System). The model is the medium; the comparison is
the deliverable.

This document consolidates what each leg produced. For deeper depth in any
leg, follow the pointers to that leg's own CLOSEOUT / FINDINGS / README.

---

## 1. The three legs in one paragraph each

**netflow** (`/home/fig/soultest`, FROZEN) — Python. Hand-rolled
scalar-conservation-network solver: `Node` holds a scalar state, `Edge`
computes a conserved flux, sparse residual assembled by hand, damped Newton
+ scipy sparse LU. Built one full physics plugin (`netflow.plugins.thermal`)
with multiple components, fluids cache (CoolProp HEOS backend), materials
catalog. Scales to ~380k nodes (~1/8 PWR core) in ~190 s steady. Verified
to textbook closed form; code-compared against VERA P6/P7 (the project
specifically learned that VERA P6/P7 supplies *code comparison* not
*validation* — netflow's biggest internal correction).

**soultest-julia** (`/home/fig/soultest-julia`, FROZEN) — Julia /
ModelingToolkit. Same physics chain on plain MTK + MTKStandardLibrary.
Custom stream `FluidPort` because no IF97 MTK binding ships; constant cp
proxy. Matched netflow node-by-node to **25 mK** with the same closures.
Built slices 1–10, including signal+thermal Doppler (MTK-F7), parallel
momentum (MTK-F8), axial conduction (MTK-F10/F11). **Hit a compile wall** at
multi-pin assembly: `mtkcompile` scalarises per-component, exponent ~N^1.6,
extrapolated 25–40 minutes for 17×17×30 — never run, only extrapolated.
Soul findings SOUL-F-a..f.

**soultest-modelica** (`/home/fig/soultest-modelica`, this leg) — Modelica
4.1.0 / Dymola 2026x, headless via Python `DymolaInterface`. Same physics
chain, idiomatic Modelica using `HeatPort_a/_b` + `Modelica.Fluid.Interfaces.FluidPort_a/_b`
(stream connector, Franke 2009) + `Modelica.Media.Water.StandardWater` (IAPWS-IF97).
**Climbed Julia's full ladder (slices 1–10) and past it**: completed 17×17×30
assembly (Julia's "untestable" anchor) in **397 s end-to-end**. Two distinct
walls characterised. 14 Modelica/Dymola capability findings + 6 Soul findings,
4 upstreamed (SOUL-F032..F035).

---

## 2. Headline comparison

| Axis | netflow (Python) | soultest-julia (MTK) | soultest-modelica (Dymola) |
|---|---|---|---|
| **Solver paradigm** | hand-rolled sparse Newton | acausal symbolic (connect()-emitted) | acausal symbolic (connect()-emitted) |
| **Conservation pattern** | hand-assembled residual | `connect()` symbolic | `connect()` symbolic |
| **Coolant medium** | CoolProp HEOS (IAPWS-95) | constant cp = 5500 (no IF97 binding) | **Modelica.Media IF97 out of the box** |
| **Match vs re-measured netflow** | reference | 25 mK (with quadratic property fits) | **24.7 mK aligned, 0.34 K native IF97** |
| **Single-pin solve time** | 9 ms (Newton only) | 0.064 s @ 10k mesh | 3.7 s end-to-end (translate + compile + sim) |
| **Component LOC (this physics)** | ~1342 (full plugin) | 98 (using MTKStdLib) | 430 (using MSL) |
| **Slice ladder reached** | n/a (one full plugin) | 1–10 | 1–10 + assembly stress |
| **Doppler feedback (signal+thermal)** | (separate plugin) | yes (MTK-F7) | yes (MO-F10), exact equilibrium |
| **Parallel-channel flow split** | special-cased ṁ=0 | poly-algorithm escapes (MTK-F8) | bit-exact (MO-F11) |
| **Zero-conductance edge** | n/a | Unstable retcode (MTK-F11) | runs clean (MO-F12) |
| **17×17×30 PWR assembly** | reachable | **extrapolated 25–40 min, never run** | **397 s end-to-end (Assembly17x17); 433 s vanilla VERA-P6-parameterised** |
| **Past Julia's anchor (18×18×30, 20×20×30)** | reachable | **extrapolated, never run** | **454 s, 645 s — clean on slope-1.38** (MO-F20) |
| **22×22×30** | reachable | not measured | **cc1 OOM-killed at 19.9 GB resident** (MO-F20) — RAM ceiling, not time ceiling |
| **25×25×30** | reachable | not measured | **not reached — 22×22 ceiling hits first** (open: `gcc -O0`/`tcc` mitigation) |
| **VERA P6 code-comparison (power-driven spread)** | included in plugin | not tested | **1.5 K** vs Kelly 6.6 K CTF/VERA, 8.7 K COBRA-IE (MO-F21) — gap structurally explained by no-guide-tube model topology |
| **Cross-pin axial conduction at 17×17×30** | (in plugin) | not tested | **YES — 543 s (+25 % vs vanilla)** (MO-F17) |
| **Per-pin neutronics feedback at assembly scale** | (separate plugin) | not tested | **YES at 17×17×10 — 135 s; 17×17×30 deferred** (MO-F18) |
| **Subchannel cross-flow at 17×17×30** | (in plugin, calibrated mix) | not tested | **YES — 621 s (+43 % vs vanilla)** (MO-F19; requires linear ΔP closure) |
| **Sparse-solver effect on init-bound walls** | n/a | tuned escape gated (untestable) | **2.2× on chain N=2500; rescues N=5000 (which failed at defaults)** (MO-F15) |
| **Sparse-solver effect on compile-bound walls** | n/a | n/a | within 3 % of default (cc1 dominates) (MO-F16) |
| **Where the wall lives** | sparse-LU at ~10⁶ nodes | mtkcompile codegen ~N^1.6 (per-component scalarises) | gcc `cc1` ~5 min on 174 MB C *OR* init-solver under IF97 inverses (rescued by `Advanced.Translation.SparseActivate=true`) |
| **Vendor lock** | none | partial (escape requires JuliaHub registry) | partial (Dymola license; OpenModelica is an alternative on the same `.mo`) |

---

## 3. The scaling story

Two scaling axes were tested in this leg, both with Dymola defaults (no
advanced flags — see §6).

### 3a. CoupledChain — linear topology, growing N

`NetflowModelica.Tests.CoupledChain(n=N)` — N axial slices in series, each
with its own constant-property pin radial stack + a CoolantCell.

| N axial | unknowns | wall [s] | note |
|---:|---:|---:|---|
| 10 | 608 | 4.1 | baseline overhead |
| 100 | 6,008 | 6.4 | sub-linear (overhead-dominated) |
| 1,000 | 60,008 | 41 | linear |
| 2,500 | 150,008 | 208 | local exponent ~N^1.76 |
| 5,000 | 300,008 | **wall hit** | codegen done in ~4 min; dymosim ran >10 min without converging — init solver under IF97 inverses is the cliff |

`results/scaling_coupled_chain.png` overlays this against the Julia MTK-F4
anchor (~71 s mtkcompile alone at 2 k unknowns) — Dymola does the same scale
end-to-end in ~5 s.

### 3b. 17×17 PWR assembly — parallel topology, growing pin count

`NetflowModelica.Tests.Assembly17x17(n_pin, n_axial)` — n_pin independent
parallel pin channels, each n_axial slices deep. No cross-pin coupling.

| n_pin × n_axial | pin nodes | wall [s] | note |
|---:|---:|---:|---|
| 4×4 × 10 | 160 | 8.1 | |
| 8×8 × 10 | 640 | 22.7 | |
| 8×8 × 20 | 1,280 | 41.3 | |
| 17×17 × 10 | 2,890 | 105.9 | physics verified (test/verify_assembly_physics.py) |
| 17×17 × 20 | 5,780 | 227.2 | |
| **17×17 × 30** | **8,670** | **397.1** | **Julia's "untestable" anchor — COMPLETED** |

**Scaling trajectory** (least-squares power-law on the full ladder gives
exponent ≈ 0.98, but that is misleading — the local exponent *rises*):

| segment | N ratio | wall ratio | local exponent |
|---|---:|---:|---:|
|   160 →   640 | 4.00× | 2.80× | 0.74 |
|   640 → 1280 | 2.00× | 1.82× | 0.86 |
| 1280 → 2890 | 2.26× | 2.56× | 1.16 |
| 2890 → 5780 | 2.00× | 2.15× | 1.10 |
| 5780 → 8670 | 1.50× | 1.75× | **1.38** |

The high-end exponent of 1.38 is *gcc `cc1`* eating into wall time as the
generated C grows: `dsmodel.c` at the top is **174 MB**, cc1 consumed
**11.7 GB RAM** and ~5 min of single-core CPU, producing a 164 MB
`dymosim` binary. Extrapolating *this* exponent (not the small-N regime)
the next anchor point (e.g. 25×25 × 30 = 18 750 pin nodes) lands at
~16–20 minutes — past the comfortable region without `-O0`/`tcc`
intervention. Plot: `results/stress_assembly_17x17.png`.

### Physics verification (closing the SOUL-F028 gap)

The stress test measured wall time only. Re-ran 17×17×10 with physics
checks (`test/verify_assembly_physics.py`):

- `Q_total_assembly = 19,039,320 W` — matches 289 × 18 kW/m × 3.66 m exactly.
- `T_cool_outlet_max = 602.6 K` — in the expected 600–615 K band.
- `T_centerline_hot = 1262.6 K` — matches slice-3's single-channel outlet
  centerline exactly, as expected for parallel-independent channels.

The assembly is correct, not just fast.

---

## 4. The two walls Dymola hits (and where Julia's lived)

| Wall | Where it lives | When it bites | What it means |
|---|---|---|---|
| **Julia MTK-F4/F9** | `mtkcompile` codegen (per-component scalarisation) | ~N^1.6 in unknown count; bites visibly at multi-pin assembly (extrapolated 25–40 min @ 17×17×30) | Per-component codegen path doesn't reach 10⁴–10⁵ regime without the gated `JuliaSimCompiler.jl` |
| **Dymola "gcc cc1"** | system C compiler invoked by `dsbuild.sh` on a 100+ MB generated `dsmodel.c` | bites at 17×17×20 onward; ~5 min `cc1` for 174 MB C, 11.7 GB RAM | Not Dymola — the *toolchain* — and addressable by `-O0`/`tcc` (deferred, see ideas.md) |
| **Dymola "init-solver under IF97"** | algebraic initialization solver doing IAPWS-IF97 inverse calls inside the Newton loop | N=5000 axial chain (300k unknowns) — codegen finished in 4 min, but dymosim ran >10 min without converging | Different shape: the inner-loop cost dominates the outer Newton; addressable by loosened tolerance, ConstantPropertyLiquidWater fallback, or better initial guesses (deferred) |

**Net:** Julia's wall blocks at extrapolation; Dymola's walls move much
further out and live in places that have known mitigations.

---

## 5. Soul-System findings (cross-leg view)

Findings upstreamed to `/mnt/d/Projects/Soul-System/findings/open/`:

- **SOUL-F032** — *Dogfood ceremony compresses on repeated use.* The 3rd
  leg took hours of wall-clock, the 2nd took ~2 weeks, on similar-scope
  work. Mechanism: priors cited not re-discovered; slice ladder + ADR
  template inherited from prior leg.
- **SOUL-F033** — *Acausal `connect()`-emitted conservation removes a bug
  class.* Three slices verified KCL invariants at float64 noise without a
  hand-written residual — bug class netflow had to validate against by hand
  is *structurally impossible* in Modelica/MTK.
- **SOUL-F034** — *Exclusion-naming as Accountant discipline.* Recording
  what was deferred *and why* (this leg's CONTEXT §5) prevented Julia's
  scope-creep pattern from repeating. Worked: hard stop at slice 6 held
  through the first close-out; later expansion was deliberate, not drift.
- **SOUL-F035** — *Skill-capture trigger: the "third trap from one surface"
  heuristic.* Eight headless-Dymola gotchas were each one debug cycle.
  Capturing as `SKILL.md` after the third trap pays back even on one more
  use.

Open in this leg, not yet upstreamed (would be candidates for F036+):

- The "Coherent Falsehood on measurement" pattern (the SOUL-F028 trap I just
  re-instantiated: measuring wall-time only, never verifying physics).
  Caught by the next `/soul-verify` run, fixed in 2 minutes. Worth a finding
  on *which specific shape of measurement* tends to skip the verify step.
- The "what's the inflation framing of a benchmark" pattern. Dymola's 397 s
  reads as "fast" only against Julia's 25–40 min extrapolation; absent that
  anchor, 397 s is just a number. The comparison artifact (this document)
  IS the load-bearing context.

---

## 6. Caveats (honest framing of what these numbers do and don't show)

- ~~**All Dymola runs use defaults.**~~ **PARTIALLY MEASURED (2026-05-26
  unfreeze, step 2):** `Advanced.Translation.SparseActivate` was swept against
  the three Dymola walls. SparseActivate halves the sim-bound wall (chain
  N=2500: 197 s → 90 s) and rescues the init-solver wall (chain N=5000:
  hard-failed at defaults → 228 s with sparse). At compile-bound walls
  (17×17×10, 17×17×30) no Dymola-side flag moves the wall by >3 % — cc1 is
  the bottleneck and Dymola flags don't reach it (MO-F15, MO-F16; headline
  plot `results/unfreeze_headline.png` panel A). Tuning still uncovered:
  `gcc -O0`/`tcc` (toolchain mitigations, not Dymola flags); KLU vs Pardiso
  selection in `Hidden.SparseSolverType` (Dymola 2026x defaults used).
- ~~**The 17×17 assembly is parallel-independent.**~~ **CLOSED (2026-05-26
  unfreeze, step 3):** three physics-breadth extensions built MSL-only and
  run at 17×17×30 — cross-pin conduction (MO-F17, 543 s, +25 % vs vanilla),
  pin-by-pin neutronics feedback (MO-F18, runs at 17×17×10 in 135 s;
  17×17×30 transient deferred), subchannel cross-flow (MO-F19, 621 s,
  +43 %). The parallel-independent caveat is closed; the no-cross-flow
  caveat is closed; the kinetics-at-assembly caveat is closed at 17×17×10.
  Headline plot `results/unfreeze_headline.png` panel B.
- **Subchannel cross-flow needs an explicit pressure-drop closure** (MO-F19).
  Direct connect of 4-port lateral cells is structurally singular under the
  no-momentum slice-4 choice; a linear `m_flow = G * Δp` element
  (`Components.LateralFlowLink`) closes the system. The conductance `G` is
  tuned to a topology-test value (1e-5 kg/(s·Pa)), not physically
  calibrated against CTF or netflow; quantitative cross-flow magnitudes
  would need calibration.
- **One machine, one Body, one moment in time.** All three legs measured
  on the same WSL2 Linux 6.6 box. Cross-OS / cross-machine generalisation
  not claimed.
- **netflow's 9 ms vs Dymola's 397 s is not a fair time comparison.**
  netflow's number is pure Newton; Dymola's includes translate + symbolic
  manipulation + C codegen + gcc compile + dymosim init + sim. The right
  axis is *was it possible at all* and *did the bottleneck shift the way
  the comparison predicted* — both answered.
- **No measured-data validation in any leg.** Data-ceiling guardrail
  carried from netflow's lesson. The strongest claim any leg makes is
  "code-comparison against an independently-derived analytic" or
  "code-comparison against another solver." Never "validated."

---

## 7. What is in each leg's repo

| Item | netflow | soultest-julia | soultest-modelica |
|---|---|---|---|
| Frame | `CONTEXT.md` | `CONTEXT.md` | `CONTEXT.md` |
| Abstraction-layer ADR | spec doc | `docs/adr/0001` | `docs/adr/0001` |
| Findings ledger | `docs/expert-qa.md`, ADRs | `docs/FINDINGS.md` (12 + 6) | `docs/FINDINGS.md` (14 + 6) |
| Closing finding | (frozen baseline doc) | `CLOSEOUT.md` | `CLOSEOUT.md` |
| Headline plots | `docs/paper/*.pdf` | `results/*.png` | `results/*.png` (3 scaling + 2 slice visual) |
| Benchmark scripts | `bench/vera_codecompare.py` | `bench/scaling_*.jl` | `bench/scaling_coupled_chain.py`, `bench/stress_assembly_17x17.py`, `bench/remeasure_netflow.py`, `bench/end_to_end_timing.py` |
| Slice tests | tests under `tests/` | `test/slice1..10.jl` | `test/slice1..10_*.py` + `verify_assembly_physics.py` |

---

## 8. What this triangulation *is* and *isn't*

**It is** a fair-defaults, same-physics, same-Body, same-machine comparison
of three solver paradigms on a bounded model. Each leg's CLOSEOUT calls
itself frozen. The pattern (frame → slice → verify → close → upstream)
held in all three.

**It isn't** a benchmark of the absolute best each tool can do (none of
them is tuned). It isn't a recommendation that Modelica is "better" — it
is a recommendation about *where each paradigm's wall lives* and *how far
out before tuning*. For most pre-design thermal-hydraulic work bounded by
"this is the wall I'd hit on my laptop today," Modelica/Dymola defaults
appear to give the most headroom on this kind of model — which is the
finding that should land back in the Body's reference frame.

---

## 9. Next-question candidates (the Body decides)

In rough order of "most informative per unit of work":

1. ~~**Advanced-flag dogfood.**~~ **CLOSED 2026-05-26 (step 2):**
   `Advanced.Translation.SparseActivate` swept; sim walls halved, init wall
   rescued, compile wall unchanged. See MO-F15/F16.
2. ~~**17×17×30 with axial coupling (slice 10 at assembly scale).**~~
   **CLOSED 2026-05-26 (step 3a):** AssemblyVeraP6CrossPin runs at
   17×17×30 in 543 s (+25 %). See MO-F17.
3. **OpenModelica leg.** Same `.mo` package, different translator + codegen.
   Removes the vendor caveat from the comparison; isolates "Modelica as a
   language" from "Dymola as an implementation." *Still open.*
4. **`gcc -O0` / `tcc` mitigation of the cc1 compile wall.** Step 2 closed
   the Dymola-flag side; the cc1 wall remains addressable via the toolchain
   (not via `Advanced.*`). *Open.*
5. **Calibrated lateral conductance in subchannel model.** MO-F19's
   `LateralFlowLink` uses a topology-test G = 1e-5 kg/(s·Pa); a physically
   meaningful G would need cross-comparison against CTF or netflow's
   subchannel closure. *Open.*
6. **Pin-by-pin neutronics at full 17×17×30 transient.** Step 3b ran at
   17×17×10 (135 s); full 17×17×30 transient deferred. *Open.*
7. **Scale past 25×25** (e.g. 33×33×30 = 32 670 pin nodes). Step 4 will
   reveal whether the cc1 wall slides or the 16 GB RAM ceiling bites first.
   *In progress.*
4. **The closing Soul findings** (Coherent-Falsehood-on-measurement and
   benchmark-anchor-context patterns) — graduate to amendments if a third
   instance lands.

---

*This document is the cross-leg artifact. Each leg's own CLOSEOUT remains
the in-leg detail.*
