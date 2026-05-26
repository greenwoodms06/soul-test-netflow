# ADR-0002 — MSL-only constraint carries through every assembly-scale extension

**Status:** accepted
**Date:** 2026-05-26
**Decision-maker:** Body (greenwoodms06@gmail.com)
**Supersedes:** none
**Related:** ADR-0001 (the original MSL HeatPort + StreamFluidPort + IF97 decision)

## Context

The project is being **unfrozen** from its CLOSEOUT state for a three-experiment program: advanced-flag dogfood, scale past Julia's anchor (25×25×30, possibly 33×33×30), and push physics breadth to parity with netflow at assembly scale (cross-pin axial conduction, pin-by-pin neutronics feedback, subchannel cross-flow). Plus a VERA P6/P7 code-comparison anchor.

The Researcher reach-out (`/soul-expand` 2026-05-26 part 2) named **TRANSFORM** (ORNL Modelica nuclear library) and several other third-party Modelica libraries (ClaRa, ThermoPower, ThermoSysPro, ThermoFluidStream) as candidate sources for components we'd otherwise hand-roll. By Mind Rule #1 ("Use MSL primitives; don't reinvent") generalized one level up, TRANSFORM would be the natural source for cross-pin conduction, subchannel cross-flow, and assembly-scale neutronics feedback primitives.

The Body's explicit direction: **do not use TRANSFORM or any other third-party Modelica library**. Push only on MSL. The goal is to see how far **Modelica-as-a-language + MSL + Dymola** can go relative to netflow's hand-rolled Python — a paradigm-level comparison, not a library-curation comparison.

## Decision

**The MSL-only constraint from ADR-0001 (slice 1) carries through every assembly-scale extension.** No third-party Modelica libraries are used in steps 0–4 of the unfreeze program. Specifically excluded:

- **TRANSFORM** (ORNL)
- **ClaRa**
- **ThermoPower**
- **ThermoSysPro**
- **ThermoFluidStream**
- Any other library outside `Modelica.*` (the Modelica Standard Library 4.1.0 namespace).

Permitted: `Modelica.Thermal.HeatTransfer.*`, `Modelica.Fluid.*`, `Modelica.Media.Water.StandardWater`, `Modelica.Blocks.*`, `Modelica.Mechanics.*` (if relevant), `Modelica.SIunits` — i.e. everything that ships with Dymola 2026x as MSL.

### What this commits us to

1. **Cross-pin axial conduction** uses `Modelica.Thermal.HeatTransfer.ThermalConductor` between adjacent FuelPin centerline ports. The slice-10 pattern, replicated as connectivity at assembly scale.
2. **Pin-by-pin neutronics feedback** uses the slice-7 Doppler-feedback pattern (Modelica equation block + parameter) replicated × 289 pins with a shared power normalization through `Modelica.Blocks.*` signal routing.
3. **Subchannel cross-flow** uses `Modelica.Fluid.Fittings.*` pressure-loss components and `Modelica.Fluid.Vessels.*` mixing volumes — Modelica's stream connector handles the bi-directional upwind enthalpy at each cross-flow junction.
4. **No general-purpose nuclear library imported.** The model is written from MSL primitives outward, the same way slice 1 was.

## Alternatives considered

- **Build on TRANSFORM for the physics-breadth extensions** — rejected by Body 2026-05-26. TRANSFORM is the Body's professional library; using it would conflate "what TRANSFORM-the-curated-library has" with "what Modelica-the-language can express on its own primitives." The cross-paradigm comparison axis is "Modelica from primitives" vs "netflow from primitives." TRANSFORM compared to netflow would be a different (and also valid) study — not this one.
- **Permit MSL-adjacent libraries that ship with Dymola** (ThermoFluidStream is bundled, for example) — rejected. The line "MSL only" is sharp; "MSL plus what Dymola happens to bundle" is fuzzy and vendor-dependent.
- **Only restrict for steps 3a–3c (physics breadth), allow tuning libraries in step 2** — rejected. Step 2 is *flags*, not libraries; the constraint applies to libraries, so step 2 is unaffected. The flag-vs-library distinction is clean and doesn't need an exception.

## Consequences

**Positive:**
- The cross-paradigm finding is sharper: "MSL + Dymola at PWR-assembly scale" vs "Python + scipy.sparse at PWR-assembly scale" — apples to apples on "from primitives."
- The COMPARISON.md headline "where does each paradigm's wall live" is paradigm-attributable, not library-attributable.
- The Soul-finding upstream filter ("is this Soul-meta or paradigm-content?") gets a cleaner test surface: anything attributable to TRANSFORM would have been ambiguous; pure-MSL is clearly paradigm-content.
- Future "TRANSFORM-vs-MSL on the same chain" becomes its own well-scoped study, deliberately bracketed off.

**Negative:**
- We almost certainly rebuild patterns TRANSFORM has solved. Cost is hand-roll work, not correctness — MSL has the primitives; the assembly is the work.
- If a wall is hit that TRANSFORM would not hit (e.g. an init-strategy TRANSFORM has tuned), we will record it as the MSL/Dymola wall and not pre-empt it with TRANSFORM's pre-baked solution. This is the intended trade-off, not a bug.
- Subchannel cross-flow on MSL primitives may need careful Modelica.Fluid topology choices; if MSL doesn't have an obvious primitive, that itself is a finding ("the wall is in MSL's expressive coverage, not in Modelica or Dymola").

**Open questions / deferred:**
- A future "TRANSFORM leg" remains a valid follow-on dogfood (the "use vs build" comparison) — out of scope here by deliberate choice, not by oversight.

## How we will know this was right

- Each step 0–4 deliverable cites only `Modelica.*` imports — visible in any `.mo` file's `import` section.
- The COMPARISON.md update can credibly say "no third-party libraries on either side"; the netflow leg used scipy + CoolProp (system tools, not nuclear libraries), this leg uses MSL + IF97 (system tools, not nuclear libraries).
- Soul-meta findings from this push pass the project-paradigm vs Soul-meta diagnostic test (the one added to the seed §Reference Projects 2026-05-26) — they should be **Modelica-paradigm content**, staying home, not Soul-meta. The MSL-only constraint makes this diagnostic easier to apply because the lessons cannot be attributed to a curated library's choices.

---

**Source:** Body's explicit scope decision 2026-05-26 ("don't use TRANSFORM. i just want you to independently push on from other libraries. the goal is to see how far modelica can be used as compared to netflow."). Generalizes ADR-0001 across all subsequent assembly-scale extensions.
**Adopted:** 2026-05-26
**Status:** active
