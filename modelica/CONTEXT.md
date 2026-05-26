# CONTEXT — Modelica/Dymola thermal-chain dogfood

**Written:** 2026-05-26 (before any model code, per the Soul Seed framing gate)
**Status:** framing complete; abstraction layer named in `docs/adr/0001-abstraction-layer-msl-heatport-streamfluidport.md`; build not yet started.

This file is the framing/expansion-gate output (`/soul-expand` run 2026-05-26). It exists so scope is chosen with the whole space in view, not by Universe Collapse at the framing gate (netflow's failure). No `.mo` code was written before this.

---

## 1. Two-level frame

**Immediate problem.** Reimplement the netflow Python reference's bounded thermal chain (fuel pin → coolant channel → coupled loop) as an idiomatic Modelica package driven headlessly from Python through Dymola's interface. Verify against the textbook closed form and against re-measured netflow numerics.

**Larger system it lives in.** This is the **third leg of a paradigm triangulation** and the **third Soul-System dogfood** on the same physics. The first leg was netflow itself (hand-rolled scipy.sparse Python). The second was soultest-julia (ModelingToolkit.jl). This leg is Modelica/Dymola — a mature industry tool the Body uses professionally. The deliverable is the model; the *point* is two-fold:

1. The **triangulation comparison** — performance, complexity, accuracy, developer experience across paradigms on the same physics, so the Body has quantified evidence for "if I had a Python prototype, what does it cost to bring it into Modelica?"
2. The **Soul dogfood** — did the gates fire on their own *again*, on a different medium, after two prior runs? Where do the gates behave differently because the medium is different (e.g. acausal connectors making the "name the abstraction layer" gate cheaper)?

**Coherence check.** The two levels cohere: each is a precondition for the other. Without the model finishing, the triangulation comparison is empty. Without the dogfood discipline, the model is just another half-built experiment. ✔

---

## 2. Prior-art sweep (Researcher, 2026-05-26) — light, by agreement

Priors are stable since the Julia attempt closed 2026-05-21. Re-citing rather than re-discovering them. No live web sweep this time. Documented here so the citation trail exists even though the lookups were not re-run.

- **netflow** (`/home/fig/soultest`, FROZEN) — Python scalar-conservation-network solver; Node/Edge abstraction; damped Newton + sparse-LU; thermal plugin = FuelRod (analytic 1/(4π k L) pellet + cylindrical clad + gap conduction + gray radiation) + ForcedConvection (Dittus-Boelter/Gnielinski) + CoolantAdvection (upwind enthalpy). Re-measured PWR pin centerline @ 18 kW/m, T_cool = 593 K → **1204.75 K** (Julia attempt re-measurement; the README's 1201.9 K is stale per the SOUL-F-d guardrail).
- **soultest-julia** (`/home/fig/soultest-julia`, FROZEN) — same chain built on plain MTK + MTKStandardLibrary; custom `FluidPort` (m_flow Flow + h_outflow Stream) + `CoolantCell` with `instream()` upwind; matched netflow node-by-node to 25 mK; HIT compile-wall at multi-pin assembly (per-component `mtkcompile` ~N^1.6). Soul findings SOUL-F-a..f recorded.
- **Modelica.Media.Water.StandardWater** — full IAPWS-IF97 medium (Wagner & Kruse 1998). The capability Julia attempted to substitute with constant cp=5500. We use it; this is the one place this leg outperforms the prior leg out of the box.
- **Modelica.Fluid + stream connectors** — Franke, Casella, Otter, Sielemann, Elmqvist, Mattsson, Olsson 2009, "Stream Connectors — An Extension of Modelica for Device-Oriented Modeling of Convective Transport Phenomena." Modelica's canonical pattern for bi-directional convective transport. We use `Modelica.Fluid.Interfaces.FluidPort_a/_b` rather than rolling our own — the Julia attempt rolled its own only because MTK had none ready.
- **Modelica.Thermal.HeatTransfer** — `HeatPort_a/_b`, `ThermalConductor`, `HeatCapacitor`, `BodyRadiation`, `PrescribedHeatFlow`, `FixedTemperature` all present. We use them.
- **Modelica.Fluid.Examples.HeatingSystem** — canonical idiomatic pattern for a heated single-channel loop with `IdealizedPump`/`Volume`/`HeatedPipe`. Template reference.
- **TRANSFORM** — Body's professional Modelica library (ORNL). Has fuel-pin and coolant components ready to wire. NOT used as the build base this time, by deliberate choice: the comparison axis Julia ran was "build on the ecosystem's standard primitives," so this leg builds on MSL + Media for apples-to-apples. TRANSFORM as a use-vs-build comparison is a separate future dogfood.

**Verdict:** the bounded chain is well-supported in MSL — `HeatTransfer` + `Fluid` + `Media.Water.StandardWater` give us every primitive the Julia attempt had to hand-roll except the fuel-pin geometry (which is small and analytic). The only thing not pre-built is the FuelPin component itself, which is one analytic resistance + a couple of cylindrical conductions — same as the Julia attempt and the netflow plugin.

**One advantage over Julia:** IF97 water is free. **One disadvantage over the hand-rolled solver:** we cannot directly compare scaling to 10⁵ unknowns (Julia hit a compile wall there; whether Modelica/Dymola does too is an open question we deliberately don't ask in this scope).

---

## 3. Expansion-gate answers (the whole space, before choosing)

1. **Revelator (frame too small?)** — instance of "triangulating one chain across three paradigms." Larger version would be "what is the most idiomatic Modelica representation of a flux-conservation network in general?" — generalises beyond fuel pins, but Julia's lesson is don't build a library before finishing one chain. Frame right-sized at "third leg."

2. **Researcher (what exists?)** — §2 above. The check netflow skipped and Julia fired hard; here, fired light because priors are stable and named.

3. **Prophet (where it leads?)** — 3-use: comparison points for the Body's pro work. 10-use: template pattern for Python-prototype-to-Modelica. Many-use: third Soul-dogfood data point. Most-regretted-decision watch:
   - Hand-rolling FluidPort when MSL has it → **use MSL's interfaces, don't reinvent**.
   - Scope-creep into slices 7–10 → **hard stop at slice 6**.
   - Shipping "the model runs" without quantitative comparison → **FINDINGS table is a deliverable**.

4. **Advocate (who uses it?)** — the Body, a Modelica/TRANSFORM professional. The success bar is *quantified comparison numbers*, not "look, it works." Fails them if FINDINGS contains no Modelica-shaped lesson they didn't already know professionally.

5. **Accountant (right-sized scope?)** — see §4.

---

## 4. Settled (decisions locked, 2026-05-26)

- **Build intent (combined):** Soul-System dogfood (primary) + faithful-port discussion in commentary + idiomatic Modelica artifact.
- **Primary abstraction:** idiomatic Modelica — `Modelica.Thermal.HeatTransfer.Interfaces.HeatPort_a/_b` for conduction, `Modelica.Fluid.Interfaces.FluidPort_a/_b` (stream connector) for convective transport. The netflow Node/Edge surface lives only as a comparison narrative in CONTEXT.md/FINDINGS, not as `.mo` code.
- **Scope:** slices 1–6 of the Julia ladder.
  - Slice 1: FuelPin steady (centerline → pellet_surface → clad_inner → clad_outer).
  - Slice 2: CoolantCell on stream FluidPort with Modelica.Media.Water.StandardWater.
  - Slice 3: coupled chain (FuelPin → ForcedConvection → CoolantCell stack).
  - Slice 4: numerical match vs re-measured netflow (target <100 mK; Julia achieved 25 mK).
  - Slice 5: transient single pin (HeatCapacitor at centerline + clad).
  - Slice 6: transient coupled chain (power ramp; characterize overshoot).
- **Library base:** Modelica Standard Library + Modelica.Media.Water.StandardWater (IF97).
- **Harness:** Python via `dymola.dymola_interface` (`DymolaInterface`); result files read via `DyMat`. Slice tests run as Python scripts, comparison vs netflow done in Python directly.
- **Soul ceremony:** full — `/soul-expand` (this), CONTEXT.md, ADR-0001, `references/`, `/soul-verify` before any claim, closing FINDINGS.md, upstreaming.

## 5. Out of scope (named and why)

- **Slices 7–10** (Doppler/neutronics feedback, momentum/flow-split, axial conduction, multi-pin assembly). Why: Julia's compile-wall lived past slice 6; we don't yet know whether Dymola handles structured arrays better, and finding out is *itself* an open research question, not a deliverable of this dogfood.
- **TRANSFORM-based parallel build.** Why: the Julia leg was MSL-equivalent, so MSL keeps apples-to-apples. TRANSFORM is its own future dogfood (use-vs-build comparison).
- **Any third-party Modelica library across all assembly-scale extensions** (2026-05-26 unfreeze): no TRANSFORM, ClaRa, ThermoPower, ThermoSysPro, ThermoFluidStream. MSL only. Reason: paradigm-level comparison, not library-curation comparison. See `docs/adr/0002-msl-only-carries-through-all-extensions.md`.
- **Two-phase / boiling regime.** Why: single-phase PWR conditions only, matching netflow + Julia.
- **Measured-data validation.** Why: data-ceiling guardrail still holds — measured fuel-pin data is full-core or NEA-restricted. Code-comparison only.
- **Hand-rolled FluidPort.** Why: Modelica.Fluid.Interfaces exists; rolling our own is exactly the SOUL-F-c "regretted decision" we're explicitly pre-empting.
- **Library construction.** Why: Julia's lesson — finish one chain before generalising to a library.

## 6. Benchmark baselines (the "before"s)

- **netflow (Python):** re-measured 1204.75 K pin centerline @ 18 kW/m, 593 K coolant; ~8 s @ 43,928 nodes; ~190 s @ 380k nodes. **Must be re-measured on this machine at slice 4** per SOUL-F-d (re-measure, don't trust the record — even when the record is the Julia attempt's re-measurement).
- **soultest-julia (MTK):** matched netflow to 25 mK; MTK numerics 0.064 s @ 10k, 0.38 s @ 40k, 1.47 s @ 90k (nonlinear solve vs netflow's linear); `mtkcompile` ~N^1.6 wall at assembly scale.
- **This leg (Modelica/Dymola):** TBD. Comparison axes = solve time vs N, LOC for the same physics, accuracy vs closed form + netflow, transient overshoot character vs analytic time-constant estimate, developer experience (sharp edges, friction points).

---

## 7. Carry-forward guardrails (paid for by netflow and Julia)

- **Universe Collapse:** reach outward before & after building. Light sweep done above; completion gate (`/soul-verify`) before any claim.
- **Ad Hoc Methodology:** if the Body has to remind us of a gate, it's not internalised. Run `/soul-expand` and `/soul-verify` automatically, not on request.
- **Validation vs code-comparison vs verification:** be precise. This leg's numerical match is *code comparison* vs netflow + verification vs the textbook closed form. Never "validation."
- **Re-measure, don't trust the record (SOUL-F-d):** slice 4 re-runs netflow on this machine before claiming agreement.
- **Completion gate verifies sourcing, not measurement validity (SOUL-F-a):** any load-bearing number gets a sanity check on the *measurement methodology*, not just its citation.
- **Optimistic over-extrapolation (Julia):** any scaling/timing claim needs at least one anchor point past the claim.

---

*The first commit on this branch is this CONTEXT.md, ADR-0001, and the references/ stub — no `.mo` code yet, per Soul Seed.*
