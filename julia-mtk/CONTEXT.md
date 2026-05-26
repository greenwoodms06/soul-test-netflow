# CONTEXT — Julia MTK thermal-chain dogfood

**Written:** 2026-05-21 (before any model code, per `HANDOFF.md` §3)
**Status:** framing complete; decisions made (§5); abstraction layer named in
`docs/adr/0001-abstraction-layer-acausal-thermal-fluid.md`. Build not yet started.

**Decisions (Body, 2026-05-21):** tool = **plain MTK + StdLib**; chain =
**fuel-channel→coolant→loop**; fidelity = **steady-state first, then dynamic if it
holds**. Added goal: this is also a **technical benchmark vs netflow** —
performance, complexity, cost, accuracy, and capability (how easily it extends
toward subchannel / partial / full core).

This is the framing/expansion-gate output. It exists so scope is chosen with the
whole space in view, not by Universe Collapse at the framing gate (netflow's
failure). No Julia was written before this.

---

## 1. Two-level frame

**Immediate problem.** Build ONE bounded, acausal thermal-chain model in
Julia/ModelingToolkit — a small power-plant thermal loop — that runs, is verified,
and is grounded in external references.

**Larger system it lives in.** This is a **dogfood of the Soul System**. The
deliverable is the model; the *point* is the process. Success = the Soul gates
firing on their own — the framing/prior-art gate forcing the prior-art question UP
FRONT, and the completion gate catching overclaims before the Body does. netflow's
whole lesson was **Universe Collapse** (building before checking what exists). The
test is whether this build avoids re-instantiating that.

**Coherence check.** The two levels cohere: the model is the medium through which
the process is exercised and measured. The model finishing is a *precondition* for
the process comparison (netflow→this) to mean anything. ✔

**Honesty note on the dogfood metric.** The framing+prior-art gate *did* fire
before any code this session — but it fired because `HANDOFF.md` (inherited
doctrine) mandated it, not because a live Body pushed in the moment. That is the
intended state (internalized doctrine, not human reminder), but it is not yet
proof the gate fires absent any prompt. The real test is the *completion* gate
later: does it catch an overclaim the Body hasn't flagged?

---

## 2. Prior-art sweep (Emissary, 2026-05-21) — done BEFORE any code

Three parallel live web sweeps (not from memory). Sources captured in
`references/` (to be created). Headline findings:

- **ModelingToolkitStandardLibrary.jl** provides lumped **Thermal** (`HeatPort` =
  T/Q_flow across/through; HeatCapacitor, ThermalConductor/Resistor,
  ConvectiveConductor/Resistor, BodyRadiation, sources, sensors) and **Hydraulic**
  (`IsothermalCompressible` only: pressure/mass-flow — **no temperature, enthalpy,
  or phase**). Modelica-style across/through connectors confirmed.
  - docs: https://docs.sciml.ai/ModelingToolkitStandardLibrary/stable/
- **No two-phase / steam / IF97 / Rankine / turbine** anywhere in the standard
  library. Absent by design.
- **No "Julia TRANSFORM" and no ThermoPower port exist.** ThermoPower stays
  Modelica-only. Julia's nuclear ecosystem is neutronics (NuclearToolkit.jl,
  NeutronTransport.jl), not systems thermal-hydraulics.
- **Closest power-cycle code:** `Ai4EComponentLib.jl` — dormant (last push
  2024-07), 33★, and **quasi-static state-point** analysis (IsobaricProcess,
  IsentropicProcess… + CoolProp), *not* dynamic equipment with mass/energy/momentum
  balances. A wiring reference at most — does NOT make this a use/extend project.
  - https://github.com/ai4energy/Ai4EComponentLib.jl
- **Property packages are mature and reusable** — Clapeyron.jl (279★, active
  2026-05-21, IAPWS-95), CoolProp.jl (full IF97), SteamTables.jl / XSteam.jl
  (pure-Julia IF97). None ship `@register_symbolic` MTK glue — register calls +
  derivatives at the MTK boundary ourselves.
- **Dyad** (JuliaHub) is source-available (compiler ~PolyForm-Strict; std libs
  BSD-3), free for personal/non-commercial but **gated** behind a JuliaHub account
  + closed `DyadRegistry`. Lowers to MTK. Its std libs cover the **same** thermal/
  hydraulic domains as MTKStdLib — **no Rankine/thermal-fluid head start.** v3.0
  shipped 2026-05-19; fast-moving surface (3 majors in 11 months).
  - https://help.juliahub.com/dyad/dev/manual/faq.html
- **A fuel-channel→coolant→loop demo exists nowhere in Julia** — genuinely
  greenfield.

**Verdict:** the bounded chain does NOT exist in mature form → this is a **build**,
not a use/extend. But: **reuse the property layer** (do not code IF97), and keep
**TRANSFORM/ThermoPower as the component-contract design reference** (stream
connector with p / specific-enthalpy / mass-flow + per-component balances).

**Tool recommendation (evidence, not decree):** two independent sweeps converged
on **plain MTK + MTKStandardLibrary** over Dyad for a one-person bounded dogfood
whose goal is the *model* — fully open, no vendor gate, no thermal-fluid
disadvantage, and Dyad lowers to MTK anyway so the upgrade path stays open. The
one thing that flips this: if dogfooding *Dyad's tooling* is itself the objective.

---

## 3. Expansion-gate answers (the whole space, before choosing)

1. **Revelator (frame too small?)** — instance of "dynamic acausal equipment on a
   property backend," the ecosystem-wide gap. The larger "Julia TRANSFORM" is the
   north-star, explicitly NOT this dogfood. Durable reusable artifact = the
   *component-contract pattern*, established by one well-built chain.
2. **Researcher (what exists?)** — §2 above, by live sweep. The check netflow
   skipped; fired first this time.
3. **Prophet (where it leads?)** — guard against scope-creep toward a full plant
   and against coding our own steam properties or getting stuck behind Dyad's gate.
4. **Advocate (who uses it?)** — the Body (Modelica/TRANSFORM professional)
   evaluating whether Julia/MTK + the Soul process serve their real work. Fails
   them if it overclaims validation against a non-gold-standard reference (the VERA
   trap). "What is our reference, precisely?" must be answered before any claim.
5. **Accountant (right-sized scope?)** — one chain, one fidelity, property package
   reused, TRANSFORM-clone excluded. NOT a component library, NOT full-plant, NOT
   two-phase property code, NOT measured-data validation (data-ceiling guardrail
   holds). Reason: the netflow→this comparison needs the second build to finish.

---

## 4. Abstraction layer

NAMED — see `docs/adr/0001-abstraction-layer-acausal-thermal-fluid.md`. In short:
*a network of acausal thermal-fluid components joined by typed across/through
connectors (HeatPort: T/Q_flow; custom FluidPort: ṁ/h), with conservation generated
by MTK's `connect()` rather than hand-assembled; discretization (axial/radial/
channel) parametric so the same components scale from one pin to an assembly;
steady-state first, storage added later without changing connectors.*

---

## 5. Benchmark baseline — netflow (the "before")

The fuel-channel→coolant→loop was chosen so the comparison is apples-to-apples:
netflow solved the SAME physics with a hand-rolled solver.

- netflow abstraction: node = scalar state; edge = conserved flux; residual =
  flux-conservation at interior nodes, **hand-assembled** into `scipy.sparse`,
  damped Newton (Picard fallback). Thermal plugin: FuelRod → ForcedConvection →
  CoolantAdvection.
- netflow scale (**self-reported in the netflow README, NOT yet re-measured here**):
  17×17×30 = 43,928 nodes ~8 s; ~380k nodes (≈1/8 core) ~190 s; Newton ~7 iters;
  wall = sparse-LU fill-in. **For the benchmark these MUST be re-measured by
  re-running netflow on this machine** — README figures are the "before," not ground
  truth (netflow itself had withdrawn numbers).
- netflow verification: exact vs textbook fuel-pin closed form (re-derive the closed
  form independently). Comparison: code-to-code vs VERA P6/P7 (no reference solution
  — [[validation-vs-code-comparison]]).
- ⚠ **Caveat surfaced by the completion gate (2026-05-21):** the frozen netflow
  *README* still says "validated … against the VERA benchmark" — a residual overclaim
  that contradicts the project's own correction (VERA = code comparison). The 2026-05-20
  sweep fixed the papers/VALIDATION.md/ADR but not README. Do NOT inherit that framing;
  use the corrected `vera_codecompare.py` / `VALIDATION.md` numbers and language.
  netflow stays frozen — not edited.

**Benchmark axes (vs netflow):** performance (solve time vs N), complexity (LOC /
component count for the same physics), cost (dev effort), accuracy (same closed
form + same code comparison; netflow itself becomes a second comparison code —
code-to-code, never "validation"), capability (effort to grow N_channels / add a
phenomenon, toward subchannel/core).

---

## 6. Settled

- **Tool:** plain MTK + MTKStandardLibrary.jl. Dyad rejected: vendor-gated, no
  thermal-fluid head start, lowers to MTK anyway. Julia 1.11.9 confirmed installed.
- **TRANSFORM-in-Julia (a component library):** out of scope — bounded model only.
- **Reference/validation strategy:** verification vs textbook closed form; code
  comparison vs netflow (and the VERA path netflow already carries). NO measured-data
  validation (data-ceiling guardrail holds). Name the reference precisely before any
  agreement claim.
