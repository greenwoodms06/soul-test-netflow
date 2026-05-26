# Three thermal-fluid solver paradigms on one PWR pin / coolant chain

Same physics — UO₂ fuel pin → He gap → Zr clad → forced-convection coolant
loop at PWR conditions, slices 1 through 10 — built three times on the same
machine: hand-rolled sparse-Newton Python (**netflow**), ModelingToolkit.jl
+ MTKStandardLibrary (**soultest-julia**), and Modelica / Dymola 2026x /
MSL 4.1.0 (**this repo**). No tuned solvers, no third-party domain
libraries — each leg builds from primitives in its ecosystem's standard
library. Apples-to-apples on the comparison axis we cared about: "from
primitives in the standard library."

## What was built

- **netflow** — Python. Scalar `Node`/`Edge` abstraction, hand-assembled
  sparse residual, damped Newton + scipy.sparse LU. CoolProp HEOS (IAPWS-95)
  water.
- **soultest-julia** — ModelingToolkit + MTKStandardLibrary. Acausal thermal
  connectors from MTKStdLib; **hand-rolled stream `FluidPort` with `instream()`
  because MTKStandardLibrary doesn't ship one**; constant cp = 5500 J/kg/K
  because no IAPWS-IF97 (or IAPWS-95) binding for MTK is available.
- **this repo** — Modelica acausal connectors from MSL (`HeatPort_a/_b`, stream
  `Modelica.Fluid.Interfaces.FluidPort_a/_b`) + `Modelica.Media.Water.StandardWater`
  (IF97). 430 LOC across 6 components.

## Headline (defaults; one machine; same week)

| Axis | netflow | soultest-julia (MTK) | this repo (MSL/Dymola) |
|---|---|---|---|
| Single-pin solve | **9 ms** (Newton only) | 0.064 s @ 10k mesh | 3.7 s (translate + compile + sim) |
| Match to re-measured netflow | reference | **25 mK** (quadratic property fits) | **24.7 mK** (HEOS-aligned) / 0.34 K (IF97 native) |
| Component LOC | ~1342 (full plugin) | **98** (using MTKStdLib) | 430 (using MSL) |
| Slice ladder reached | n/a (one solver) | **1–10** | 1–10 + assembly stress |
| 17×17×30 PWR assembly | reachable (380k linear nodes, ~190 s) | **extrapolated 25–40 min, never run** | **397 s end-to-end, completed** |
| Where the wall lives | sparse-LU at ~10⁶ nodes | `mtkcompile` codegen ~N^1.6 (per-component scalarisation) | `gcc cc1` ~5 min on 174 MB C *or* IF97-inverse init solver (the latter rescued by `Advanced.Translation.SparseActivate = true`) |
| Vendor lock | none | partial — tuned escape via gated JuliaSimCompiler.jl | partial — Dymola license; OpenModelica is an alternative on the same `.mo` |

Headline chart: [`results/unfreeze_headline.png`](results/unfreeze_headline.png).

## For Julia / MTK devs specifically

We'd love your read on this. Five observations from the MTK side:

1. **MTK-F4 / F9 — `mtkcompile` per-component scalarisation hits a wall well
   before assembly scale.** ~71 s mtkcompile alone at 2k unknowns, ~N^1.6.
   Extrapolated to 17×17×30 (~40k unknowns) gave 25–40 min; we never ran it.
   Dymola's full pipeline on the same problem completed in 397 s.
2. **The tuned escape (JuliaSimCompiler.jl) is gated** behind the JuliaHub
   registry and was untestable in this study. If it shifts the picture
   meaningfully (we suspect it does), quantitative numbers from someone who
   can run it would close the comparison cleanly.
3. **No IF97 / IAPWS-95 binding for MTK** forced a constant-cp = 5500 proxy.
   The 25 mK match to netflow required quadratic property fits over the
   bounded coolant range. An IF97 binding (or `CoolProp.jl` integration) in
   MTKStandardLibrary would remove the "match only after aligning property
   formulations" caveat.
4. **MTKStandardLibrary lacks a stream `FluidPort`.** We hand-rolled one
   using the Franke et al. 2009 pattern (`m_flow` Flow + `h_outflow` Stream
   + `instream()` upwind). It worked, but bit-exact agreement with netflow's
   parallel-channel flow split (slice 8) required poly-algorithm escapes
   around the m_flow → 0 degeneracy. Modelica's `Modelica.Fluid.Interfaces.FluidPort_a/_b`
   handled the same case directly.
5. **What MTK got right:** slices 1–10 behaved exactly like Modelica did at
   the same scales — same equations, same numbers, same debugging surface.
   The acausal-symbolic paradigm is sound. The pain points were ecosystem
   gaps (IF97, FluidPort, JuliaSimCompiler gating), not the language.

## Honest caveats

- **One body, one machine, one week.** No cross-machine generalization
  claimed. WSL2 / Linux 6.6 / Dymola 2026x / MTK on Julia 1.11 / Python 3.12.
- **Code-comparison, not validation.** The strongest claim any leg makes is
  "matches another solver" or "matches an independently-derived analytic."
  Never "validated against measured data" — measured PWR pin data is full-
  core or NEA-restricted; we honored the ceiling.
- **netflow's 9 ms vs Dymola's 397 s is not a fair time comparison.**
  netflow's number is pure Newton; Dymola's includes translate + symbolic
  manipulation + C codegen + gcc compile + dymosim init + sim. The right
  axis is *was it possible at all* and *did the bottleneck shift the way
  the comparison predicted*.
- **Dymola defaults in the headline table.** Tuning shifts the picture —
  `Advanced.Translation.SparseActivate` halves the sim-bound wall and
  rescues an init-bound wall that hard-failed at defaults. At the
  compile-bound 17×17×30, no Dymola flag moves the wall (cc1 dominates;
  mitigation would need `gcc -O0` or `tcc`). Full sweep in
  [`docs/FINDINGS.md`](docs/FINDINGS.md) MO-F15 / F16.
- **The 17×17 cc1 RAM ceiling is real.** Pushed past Julia's anchor with
  18×18×30 (454 s) and 20×20×30 (645 s) — both clean on the prior slope-1.38
  trajectory — and got OOM-killed at 22×22×30 (cc1 hit 19.9 GB resident).
  25×25×30 not reached on this 16 GB box. See MO-F20.

## Reproduce

- **netflow:** `bench/vera_codecompare.py`, plus `bench/remeasure_netflow.py`
  for the 1204.75 K pin centerline baseline.
- **soultest-julia:** `bench/scaling_*.jl`, slice tests under `test/slice*.jl`.
- **this repo:** the 397 s headline = `bench/stress_assembly_17x17.py`; the
  wall-moves-with-scale chart = `bench/advanced_flag_sweep_part2.py`; the
  cross-pin / neutronics / subchannel extensions at assembly scale =
  `bench/physics_breadth_ladder.py`; the VERA P6 code-comparison =
  `bench/vera_p6_codecompare.py`.

Deeper comparison artifact: [`docs/COMPARISON.md`](docs/COMPARISON.md).
Full ledger of findings (MO-F1..F21): [`docs/FINDINGS.md`](docs/FINDINGS.md).

---

*If a number reads wrong, please tell us. The point of this exercise is to
get the picture honest — none of these three numbers is meant to be the
final word.*
