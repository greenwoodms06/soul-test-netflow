# Model details: response to CTF developer questions

Questions from field experts (COBRA-TF developers) on the model used in the
VERA comparison:

1. How are the pins modeled? Where is the thermal-conductivity physics?
2. What heat-transfer models are used?
3. How are transverse flows modeled?

---

## The one fact that bounds all answers

netflow is a **scalar conservation-network solver**. Each edge computes a flux
from its two endpoint scalar states. We conserve that flux at every node:

```
F_i = source_i + Σ flux_in − Σ flux_out = 0
```

and solve with a damped Newton over a sparse Jacobian.

There is **no momentum equation** in the core. Pressure drop, where it shows up,
is a loss-coefficient relation — not solved momentum. That fact bounds the
fidelity of everything below.

---

## 1. Pins and conductivity

Each pin is a radial resistance chain, stacked axially (≈30 slices over 3.66 m):

```
centerline → pellet_surface → clad_inner → clad_outer → coolant
```

Conductivity **is** temperature-dependent:

- **Pellet** — two nodes, using the closed form for a solid cylinder with
  uniform heat generation, ΔT = q‴r²/4k. As an edge:
  `flux = 4π·k(T̄)·L·(T_c − T_s)`.
- **k(T)** — UO₂ uses the Fink fit
  `k = 1/(0.0375 + 2.165e-4·T) + 4.715e9/T²·exp(−16361/T)`.
  Zircaloy-4 is `12.6 + 0.0048(T−300)`. Both are evaluated every Newton step,
  with dk/dT carried in the Jacobian.

**Limitation.** The pellet is two nodes, so we evaluate k at one mean
temperature instead of integrating ∫k(T)dT across the radius. UO₂ k drops ~3×
from 500 K to 2000 K, so this under-resolves centerline at high power. A proper
code meshes the pellet radially and integrates k. In netflow that is a fidelity
dial — more nodes along r — not an architecture change. The VERA runs used the
two-node form.

## 2. Heat transfer

- **Convection (clad → coolant)** — Dittus-Boelter `Nu = 0.023·Re^0.8·Pr^n`
  (n = 0.4 heating / 0.3 cooling), or Gnielinski. Re uses the subchannel ṁ/A_xs
  and hydraulic diameter; water properties from CoolProp at film temperature; h
  frozen within a step, recomputed between steps.
- **Gap** — two interchangeable models:
  - *Geometric*: helium conduction (`k_He = 2.682e-3·T^0.71`) in parallel with
    gray-body radiation σε_effA(T⁴−T_clad⁴).
  - *Empirical*: a fixed gap conductance h_gap as a contact resistance
    R = 1/(h_gap·A).
  We started geometric, found it over-predicts centerline by ~220 K (open hot
  gap, no contact term), and switched to empirical h_gap = 7500 W/m²·K for VERA.

**Limitations.** Single-phase liquid only — no subcooled boiling, no DNB/CHF, no
two-phase. The gap conductance is a fixed input, not a mechanistic gap model (no
burnup, gap closure, or fission-gas effects).

## 3. Transverse flows

Two separate mechanisms back two different results.

**Fuel-temperature / F_q result (pin array)** — lateral coupling is enthalpy
mixing only: `flux = ṁ_mix·cp·(T_a − T_b)` between neighbors, ṁ_mix a calibrated
fraction of axial flow. No lateral mass or momentum transfer.

**Coolant-spread result (subchannel)** — a 3-D pressure-flow network. Each
channel has axial segments plus lateral cross-flow edges to its four neighbors
at every level. Solving the pressure field redistributes mass: guide tubes have
low axial resistance, pull bypass flow, and starve neighbors, which run hotter.
Guide tubes show up as cool channels, as in VERA. Diffusive enthalpy mixing
rides on top; the whole thing is Picard-coupled to the thermal solve through
density.

**Main limitation.** That cross-flow is a scalar pressure-resistance network —
lateral flow is `Q = sign(ΔP)·√(|ΔP|/K)`. It is **not** the transverse momentum
equation: no lateral inertia, no momentum flux, no turbulent momentum mixing, no
void drift, no grid-spacer cross-flow. The coefficients (axial K, lateral K,
mixing fraction) are **calibrated**, like a subchannel code's mixing
coefficients but not derived from correlations. At the corrected Problem 6 flat
power, netflow's calibrated exit spread (~4.9–6.5 K) essentially matches the
published CTF/VERA value (~6.6 K, figure-derived; ~8.7 K COBRA-IE) — mechanistic
in shape, calibrated in magnitude. (Note: an earlier "~80% of 8.3 K" framing was
withdrawn — 8.3 K was not a sourced value; see `docs/VALIDATION.md` erratum.)

(In the subchannel path, the fuel-centerline overlay is a lumped hand estimate
with constant fuel k — it is for the map, not the temperature claim. The k(T)
network backs the fuel-temperature result.)

---

## Scope

netflow is not a CTF/COBRA-TF replacement. No momentum equation, no two-phase,
no mechanistic gap. The point is genericity: one unchanged scalar-network core
that also solves pipe networks and criticality eigenvalue problems, used here
for pre-design fuel/coolant scoping accurate to tens of degrees, cross-checked
against published benchmark code solutions (VERA P6/P7 — which have no reference
solution; see docs/VALIDATION.md erratum).

Honest growth paths toward a code like CTF:

| Item | Cost in this abstraction |
|---|---|
| Conductivity-integral pellet | fidelity dial (radial mesh) |
| Two-phase HTC | fidelity dial (new edge correlations) |
| Transverse momentum closure | **outside** the scalar-flux abstraction — the real boundary |

The first two fit inside the current model. The third is the genuine frontier.
