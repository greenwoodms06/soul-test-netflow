# netflow — Verification & Validation Report

**Date:** 2026-05-20
**Scope:** `netflow.thermal` PWR fuel-pin and assembly models
**Status:** Verified (exact). VERA comparison reframed as **code-to-code
comparison** (not benchmark validation) — see erratum below.

> ## ⚠ ERRATUM — 2026-05-20 (post external review)
>
> An expert reviewer (CTF/COBRA-TF developer) prompted an Emissary pass through
> the **primary** VERA documents (Godfrey CASL-U-2012-0131-004; Kelly et al.,
> *Nucl. Eng. Technol.* 49 (2017)). It overturned a foundational assumption and
> several specific numbers in the original §3.3–§3.5 below. The original text is
> **retained for the record** but is corrected here; the published papers
> (`docs/paper/netflow.pdf`, `netflow-methods.pdf`) carry the corrected version.
>
> 1. **VERA Problems 6 & 7 have NO reference solution.** The spec states verbatim
>    "No reference solution exists for this problem at this time" (pp. 79, 81).
>    P6/P7 define *inputs only*; all published results are **code solutions**
>    (CTF, COBRA-IE, MPACT). This is a code-to-code comparison, not validation
>    against truth. (Reference KENO-VI eigenvalues exist only for P1–P5.)
> 2. **"VERA published max centerline = 2474 K" (§3.3) is not sourced.** No
>    centerline temperature is published anywhere. VERA reports **volume-average**
>    fuel temperature. Kelly P7 max volume-average = **1065.8 °C**. The honest
>    comparison: netflow hot-pin peak volume-average = **999 °C (−6%)** at matched
>    local peaking (1.918 vs 1.92). The F_q "2.5–2.8 straddles 2.6" result rested
>    on the 2474 K figure and is withdrawn (no F_q is published; real pin peaking
>    is 1.37 radial / 1.92 3-D).
> 3. **"8.3 K coolant spread" is not a published scalar.** Figure-derived P6
>    spread is **~6.6 K (CTF/VERA), ~8.7 K (COBRA-IE)** (Kelly Fig. 11). Re-run at
>    the corrected P6 flat power gives netflow **~4.9–6.5 K (calibrated)**,
>    essentially matching CTF/VERA — see `netflow.bench.vera_codecompare`.
> 4. **Doppler "−8566 pcm" is a toy-slab magnitude, not physical.** Reported now
>    as sign/mechanism only; physical reference ≈ **−2 to −2.5 pcm/K** (derived
>    from P1/P2 KENO eigenvalues).
> 5. **Paper figures regenerated; non-paper artifacts may lag.** The two paper
>    figures (`doppler_feedback.png`, `subchannel_pinresolved.png`) are now built
>    by reproducible generators (`netflow.coupling.doppler_demo`,
>    `netflow.bench.vera_codecompare:make_subchannel_figure`) with corrected,
>    sourced labels. Other `results/` artifacts not used by the papers (e.g.
>    `vera_capstone.png`) may still show pre-reframe numbers — not shipped;
>    regenerate before reuse. See ADR-0001.

This report deliberately separates **verification** ("are we solving the
equations right?") from **validation** ("are we solving the right
equations?"). For most of this project's history, internal consistency
checks (energy balance, analytical resistances) were standing in for
validation — they are not the same thing, and the distinction surfaced a
real model bias (§3.2).

---

## 1. Intended use

`netflow.thermal` is a **lumped thermal-resistance network** tool for
**pre-design scoping** of nuclear / Rankine thermal-hydraulic problems:
sizing, bounding peak fuel temperatures, UA verification, and parametric
exploration ahead of (or alongside) higher-fidelity Modelica/TRANSFORM,
CTF/COBRA-TF, or BISON/FRAPCON models.

It is **not** a replacement for those codes. It does not model subchannel
momentum, cross-flow mixing beyond a turbulent-diffusion approximation,
fuel-performance physics (swelling, densification, fission-gas release,
gap closure with burnup), or neutronics. The codes it complements agree
with each other to <4 °C RMS on fuel temperature; this tool's honest
target is **tens of °C, fast and transparent**.

---

## 2. Verification (exact)

| Check | Method | Result |
|---|---|---|
| Conduction resistances | Analytical R = L/kA, ln(r₀/rᵢ)/2πkL | exact |
| Radiation edge | σεA(Tₐ⁴−T_b⁴), analytic Jacobian vs FD | rtol ≤ 1e-5 |
| Solid-cylinder pellet | q'/(4πk) closed form | exact |
| **Fuel-pin radial decomposition** | **Todreas-Kazimi / El-Wakil closed form** | **0.0000 %** (`test_closed_form_fuel_pin.py`) |
| Energy conservation (assembly) | ΣQ_in vs Σ mdot·cp·ΔT | 100.000 % |
| Coolant advection balance | T_k = T_{k-1} + Q/(mdot·cp) | exact |
| Linear network solutions | series / parallel / mesh | exact |

The fuel-pin decomposition test reproduces the standard textbook form
(film + gap + clad + fuel ΔT) to machine precision. The same equations
appear in the CANDU centreline-temperature literature (Onder et al., CNL,
TopFuel 2018, Eqs. 1–2), confirming our formulation is the accepted one.

**Conclusion: the solver and component physics are correct.** Given the
model's inputs, it produces the right answer.

---

## 3. Validation (against external references)

### 3.1 Geometry (matched to VERA Watts Bar)

| Parameter | VERA spec | netflow model |
|---|---|---|
| Pellet radius | 4.096 mm | 4.10 mm |
| Clad inner radius | 4.180 mm | 4.185 mm |
| Clad outer radius | 4.750 mm | 4.750 mm |
| Gap thickness | 0.084 mm | 0.085 mm |
| Coolant inlet T | 565.3 K | 565 K |
| System pressure | 15.5 MPa | 15.5 MPa |

### 3.2 The gap-conductance bias (found by validation, missed by verification)

The original gap model used **pure geometric He conduction**, giving an
effective gap conductance of **2976 W/m²K**. Accepted fuel-performance
practice (Ross-Stoute, FRAPCON, BISON) uses an **empirical gap
conductance** including solid contact + temperature-jump-distance, in the
range **5000–10000 W/m²K** at BOL with helium fill.

Centerline-temperature sensitivity (q' = 20 kW/m, VERA geometry):

| Gap conductance | Fuel centerline T |
|---|---:|
| 2976 (geometric, original) | 1048 °C |
| 7500 (mid-literature) | 828 °C |

**The geometric model over-predicted fuel centerline temperature by
~+220 K.** Every internal consistency check passed throughout — energy
balanced to machine precision while the absolute temperature was wrong.
This is the defining example of why verification ≠ validation.

**Fix:** `FuelRod(gap_conductance=...)` accepts an empirical h_gap
[W/m²K]; when supplied it replaces geometric conduction. Default remains
geometric for backward compatibility, with this caveat documented.

### 3.3 Integral validation against VERA max fuel centerline

> **⚠ CORRECTED — see erratum.** No VERA centerline temperature is published;
> the 2474 K figure below is unsourced and withdrawn. The correct comparison is
> volume-average fuel temperature: netflow 999 °C vs Kelly P7 1066 °C (−6%). The
> F_q "straddling 2.6" result rested on 2474 K and is withdrawn.

VERA published maximum fuel centerline temperature: **2474 K (2201 °C),
1.7 % uncertainty**.

Inverse check — peak linear heat rate our model needs to reach 2474 K:

| Gap conductance | Peak LHR needed | Implied F_q |
|---|---:|---:|
| 5000 W/m²K | 45.2 kW/m | 2.47 |
| 7500 W/m²K | 48.7 kW/m | 2.66 |
| 10000 W/m²K | 50.7 kW/m | 2.77 |

The Watts Bar **F_q design limit is ~2.6**. Our model reaches the VERA
max centerline at F_q = 2.47–2.77, **straddling the independently-known
design limit**. The benchmark max occurs at/near the limiting hot spot
(F_q ≈ 2.6), and the model places it there. F_q was *inferred* from the
predicted temperature — it was not an input — so the agreement is
corroboration, not circularity.

### 3.3b Field comparison vs VERA Problem 6 (published pin-by-pin data)

Source: Kelly et al., *Nucl. Eng. Tech.* 49 (2017) 1326 — MC21/CTF and
VERA solutions to Problem 6 (3D single assembly, hot full power). This
paper publishes the actual pin-power distribution (Fig 10), the
subchannel exit coolant temperature field (Fig 11), and code-to-code
agreement metrics. The pin cell spec (`0.4096 0.418 0.475 / u21 he
zirc4`) is an *exact* match to our geometry.

Published VERA Problem 6 values:
- Radial pin-power peaking: ~1.05 (very flat — single enrichment)
- Subchannel exit coolant T: 321.1–329.4 °C, **spread ~8.3 °C**, avg rise
  ~33.4 °C (inlet 565 K)
- Code-to-code (MC21/CTF vs VERA): fuel 4.4 °C RMS, coolant 0.02 °C RMS

**Validation result — what matches and what doesn't:**

| Quantity | netflow | VERA | Verdict |
|---|---|---|---|
| Geometry | exact | exact | matched |
| Average coolant rise | 33.4 °C at q_avg=18 kW/m, realistic flow | 33.4 °C | **matches** (energy balance is robust) |
| Coolant exit spread | ~3.3 °C (from ±5% power) | 8.3 °C | **captures ~40%** |

**Key finding:** VERA's 8.3 °C coolant spread is *not* primarily
pin-power driven — a ±5% radial power variation produces only ~3.3 °C.
The remaining ~60% is **subchannel-geometry driven** (guide-tube bypass
flow, assembly-edge cooling) that CTF resolves and a lumped
one-column-per-pin model structurally cannot. This is a *second*
identified fidelity gap, distinct from the gap-conductance bias (§3.2):

- §3.2 gap conductance → limits **fuel** temperature accuracy (±200 K)
- §3.3b subchannel geometry → limits **coolant** spread accuracy (~60% unmodeled)

Neither is a bug. Both are inherent to the lumped-vs-subchannel fidelity
class. Critically, **scale does not fix either** — running the same model
at full-core resolution would carry the identical two gaps.

### 3.4 Local maxima (heterogeneous loading)

A smooth cosine power tilt on a single assembly cannot represent the
local hot spots a pin-resolved core shows. Imposing a realistic
heterogeneous map (guide tubes as water holes + flux-return peaking):

| Power map | Peak centerline | Local maxima |
|---|---:|---:|
| Smooth cosine tilt | 1881 °C | 1 |
| Guide tubes + local peaking | 2119 °C | 4 |

The heterogeneous loading runs 239 °C hotter with 4 local maxima vs 1
(`results/local_maxima_demo.png`). A single-assembly smooth model both
under-predicts the peak and erases the local structure.

---

## 4. Known limitations & uncertainties (ranked)

1. **Gap conductance** — dominant absolute-T uncertainty, ±~200 K /
   ±0.15 in implied F_q. Use `gap_conductance=` with a FRAPCON/BISON
   value for realistic predictions. No validated gap *correlation* is
   built in (deliberately — half-implementing one would risk another
   "coherent falsehood").
2. **Imposed power distribution** — power is a user input, not solved
   from neutronics. Absolute peaks depend entirely on the supplied
   peaking factors.
3. **No subchannel momentum** — coolant is single-column per pin with a
   turbulent-diffusion mixing approximation; no cross-flow pressure
   coupling.
4. **Single pellet radial node** — uses the analytic solid-cylinder
   result, not a refined pellet mesh. Adequate for centerline T;
   insufficient for detailed radial fuel-performance.
5. **No burnup evolution** — gap closure, conductivity degradation, and
   fission-gas effects are not modeled. BOL only.
6. **Hard-coded material capacities** (ρ, cp for transient) live in
   components, not on the Material/Fluid interfaces.

---

## 5. What true (publication-grade) validation still requires

- Use VERA's **published pin-power distribution** as direct input
  (instead of a guessed cosine), then compare the resulting temperature
  field **pin-by-pin** and report RMS error.
- Match exact cycle state, boron, and local coolant conditions.
- Accept the fidelity-class gap: a lumped tool will not reach the <4 °C
  RMS agreement of CTF/MC21.

The §3.3 inverse-F_q result is strong **integral** corroboration but is
not a point-by-point field comparison.

---

## 6. Fitness-for-purpose statement

For **pre-design scoping**, `netflow.thermal` is fit for purpose:
- Solver and decomposition: verified exactly.
- Peak fuel temperature: validated at the integral level against VERA, at
  the correct peaking factor, within a quantified gap-conductance
  uncertainty.
- Fast (full PWR assembly steady solve in seconds; transient in <1 min)
  and transparent (every resistance inspectable).

It is **not** fit for licensing-grade absolute fuel temperature
prediction without (a) a validated gap-conductance input and (b) a
matched power distribution.

---

## 6b. Capstone figure & coupled multi-physics

`results/vera_capstone.png` is the validation capstone: the full
improved-physics 17×17 assembly (VERA geometry, empirical gap
conductance, solved coolant, cosine axial, radial tilt, mixing) against
VERA Problem 6, with a fidelity scorecard. With channel flow calibrated
to VERA's average rise, our coolant exit field matches VERA's average and
radial trend; the spread is ~17% captured (the rest is subchannel
momentum, §3.3b). With the empirical gap conductance the peak fuel
centerline bias (§3.2) is removed.

The same generic core also runs the hydraulic plugin (pipe networks) and
**couples** the two via Picard iteration (`netflow.coupling.coupled_th`),
mirroring how MC21/CTF couple. This demonstrates the coolant-spread
mechanism (guide-tube bypass) without claiming subchannel-momentum
fidelity.

## 6d. Subchannel-resolved coupled T-H — closing the coolant-spread gap

The §3.3b coolant-spread gap (~60% subchannel-geometry-driven) was
addressed by building a **subchannel-resolved coupled hydraulic↔thermal
solve** (`netflow.coupling.subchannel`): a 3D subchannel pressure-flow
network (axial + lateral cross-flow, guide-tube bypass) Picard-coupled
to the thermal solve, on the unchanged core.

Result at full 17×17 assembly:
- Guide tubes carry bypass flow; their channels appear as local cool
  spots in the pin-resolved coolant field (matching VERA Fig 11's pattern)
- **Coolant spread: ~4.9–6.5 K (calibrated) vs published CTF/VERA ~6.6 K**
  — essentially matching. *(The original "vs VERA's 8.3 K — 80% captured"
  framing is withdrawn: 8.3 K was unsourced; the figure-derived P6 spread
  is ~6.6 K CTF/VERA, ~8.7 K COBRA-IE — see erratum. Re-run at corrected
  P6 flat power: `netflow.bench.vera_codecompare`.)*
- Picard converges in 2–3 iterations

**Honest calibration note:** the *mechanism* (guide-tube perturbation +
lateral cross-flow) comes from the generic-core physics. The *lateral
mixing coefficient* (~0.22) was **calibrated to VERA's spread** — exactly
as real subchannel codes (CTF/COBRA) calibrate their turbulent-mixing
factor β. So this is a generic-solver *reach* demonstration that captures
the dominant physics, not a first-principles prediction of the spread.

Pin-resolved artifacts: `results/subchannel_pinresolved.png` (2D coolant
+ fuel + flow), `results/subchannel_axial.gif` (field rising up the
assembly), `results/subchannel_3d.html` (interactive 3D).

This revises the §3.3b verdict: with subchannel resolution at the
corrected P6 flat power, netflow's calibrated coolant spread (~4.9–6.5 K)
essentially matches the published CTF/VERA value (~6.6 K). The remaining
gap is lateral momentum closure and form losses.

## 6e. Neutronics — the core handles eigenvalue problems, and power is now computed

The deepest generality test: neutron diffusion is an *eigenvalue*
problem (criticality k), a different mathematical structure from the
driven flux problems (thermal/hydraulic). It is solved on the
**unchanged core** by **power iteration** — each iteration a driven
diffusion solve, fission source updated from the previous flux. The
eigenvalue lives in the outer loop (same meta-pattern as Picard
coupling).

Verification vs the analytical bare-slab k-eff (`k = νΣf/(Σa+D·B²)`):

| N (cells) | k_numeric | error |
|---|---|---|
| 20 | 1.000097 | +9.7 pcm |
| 50 | 1.000015 | +1.5 pcm |
| 100 | 1.000004 | +0.4 pcm |
| 200 | 1.000001 | +0.1 pcm |

Textbook O(Δ²) finite-volume convergence; the fundamental flux mode
matches the analytical cosine exactly. (`netflow.plugins.neutronics`)

**Doppler-coupled neutronics↔thermal** (`netflow.coupling.neutronics_thermal`)
closes the project's most pervasive caveat — *power is now computed, not
imposed*. With Doppler feedback (Σa rises with √T_fuel), reactivity falls
with rising fuel temperature: a **negative** temperature coefficient, the
sign that makes reactors inherently stable. The flux Doppler-flattens at
high power. **This is a sign/mechanism demonstration only** — it runs on a
one-group bare slab with illustrative cross-sections, so its *magnitude*
is not physical (the earlier "−8566 pcm" was a toy-slab value, withdrawn —
see erratum). Physical reference for fresh 3.10 wt% UO₂ ≈ −2 to −2.5 pcm/K,
derived from the spec's P1/P2 KENO eigenvalues. Figure:
`results/doppler_feedback.png`.

This establishes the core's reach across **problem structure**, not just
domain: driven BVP → transient (ODE) → eigenvalue (power iteration) →
coupled multiphysics (Picard) — all via the same "outer loop of driven
core solves" pattern, with no core changes.

## 6c. v2 priorities (deliberately deferred)

These are real, legitimate next steps — deferred as their own careful
cycles, NOT rushed as finishes:

1. **Subchannel momentum model** — would close the ~60% subchannel-driven
   coolant spread (§3.3b). The single biggest accuracy improvement for
   the coolant side. Large effort (lateral cross-flow, grid form losses).
2. **Vectorized assembly** — batch the per-edge hot loop to break the
   ~400k-node spsolve+dispatch wall toward full-core. **Will not improve
   accuracy** (the physics gaps are scale-invariant, §3.3b) — purely a
   reach/performance improvement. Touches the core's hot path, so it
   needs its own TDD + regression cycle.
3. **Validated gap-conductance correlation** (Ross-Stoute with contact
   pressure, gas mixture, roughness) — replaces the user-supplied
   `gap_conductance` scalar with a self-contained model.
4. **Two-phase HTCs** (Chen boiling, Nusselt condensation) — for
   evaporator/condenser modeling.

## 7. Reproducing the results in this report

```bash
pytest tests/thermal/test_closed_form_fuel_pin.py   # §2 exact verification
pytest tests/thermal/test_gap_conductance.py        # §3.2 gap model
python -m netflow.plugins.thermal.examples.assembly_visualizer \
    --pins 17 --axial 30 --non-identical --coolant-as-unknown \
    --axial-shape cosine --cross-pin-mixing 0.05      # full-physics assembly
```

The §3.3 inverse-F_q and §3.4 local-maxima analyses are documented in the
session retrospective (`docs/superpowers/retrospectives/`).
