# references/ — citation index

Local reference repository. Following the Soul-System `operations/reference-repository.md` pattern: CSL-JSON core + per-doc sidecars + held PDFs (when available + not paywalled).

Per the agreed light-sweep scoping (CONTEXT.md §2), priors are *cited* here without re-running the discovery sweep. The Julia attempt's `references/` had already established these as the relevant priors for thermal-fluid acausal modelling on Python/Julia/Modelica; this leg inherits them rather than re-running the field scan.

## Priors carried forward

### Solver paradigms compared

- **netflow** — `/home/fig/soultest/` — Python scalar-conservation-network solver. FROZEN. The Python leg of the triangulation.
- **soultest-julia** — `/home/fig/soultest-julia/` — MTK/ModelingToolkit thermal-chain dogfood. FROZEN. The Julia leg of the triangulation; CLOSEOUT.md and FINDINGS.md read.

### Modelica primitives / patterns used by this build

- **Franke, Casella, Otter, Sielemann, Elmqvist, Mattsson, Olsson (2009)** — "Stream Connectors — An Extension of Modelica for Device-Oriented Modeling of Convective Transport Phenomena," Proceedings of the 7th International Modelica Conference. Canonical reference for the stream-connector design we use in `FluidPort_a/_b`. Available at modelica.org.
- **Modelica Standard Library 4.1.0** — `Modelica.Thermal.HeatTransfer`, `Modelica.Fluid`, `Modelica.Media.Water.StandardWater`. Bundled with Dymola 2026x.
- **Modelica.Fluid.Examples.HeatingSystem** — canonical idiomatic single-heated-loop pattern; used as a wiring template.

### Thermophysical properties / closures

- **Wagner & Kruse (1998)** — "Properties of Water and Steam, IAPWS Industrial Formulation 1997," Springer-Verlag. The reference standard underlying `Modelica.Media.Water.StandardWater`. The Julia attempt could not use this directly (no MTK binding); this leg can.
- **Fink & Petri (1997)** — "Thermophysical Properties of Uranium Dioxide," ANL/RE-97/2. Used in netflow's `UO2.k(T)`; ported into NetflowModelica functions.
- **Hagrman & Reymann (MATPRO)** — Zircaloy-4 properties used by netflow's `Zircaloy4.k(T)`; same correlation here.
- **Dittus & Boelter (1930) / Gnielinski (1976)** — single-phase tube-side convection correlations. Same forms netflow's `_nu_dittus_boelter` / `_nu_gnielinski` use.

### Existing Modelica/TRANSFORM material (referenced, not used as build base)

- **TRANSFORM-Library** — ORNL's Modelica thermal-hydraulic library used by the Body professionally. Has fuel-pin, coolant, two-phase. Deliberately NOT the build base here (apples-to-apples with Julia's MSL choice). A future use-vs-build dogfood would put TRANSFORM in the build-base seat. Per ADR-0002, also excluded from the 2026-05-26 unfreeze extensions.

### VERA Problem 6/7 code-comparison anchor (loaded 2026-05-26)

**Framing (carried forward from netflow's Emissary digest 2026-05-20):** VERA Problems 6 and 7 specify INPUTS ONLY; the benchmark explicitly states "No reference solution exists for this problem at this time" (Godfrey, CASL-U-2012-0131-004, pp. 79/81). Every published P6/P7 result is a code solution (MC21/CTF, MC21/COBRA-IE, VERA/MPACT). This leg therefore performs **code-to-code comparison**, never validation — same discipline as netflow.

- **Godfrey (2014)** — CASL-U-2012-0131-004 — VERA Core Physics Benchmark Problem Specification. The input spec. Geometry, operating point, power profile shape. (netflow has the digest at `/home/fig/soultest/references/godfrey-2014-vera-spec.md`.)
- **Kelly et al. (2017)** — Nucl. Eng. Technol. 49 (2017) 1326–1338 — MC21/CTF and VERA multiphysics solutions to VERA P6/P7. **The numerical anchor.** Reports:
  - P7 max volume-average fuel pin temperature: **1065.8 °C (1338.95 K)** [Fig. 24]
  - P6 subchannel exit coolant spread (max-min over fuel channels): **6.6 K (MC21/CTF and VERA), 8.7 K (MC21/COBRA-IE)** [Fig. 11]
  - P7 3D local pin-power peaking max: **1.92**; radial peaking max: **1.37**
  - P6 1/4-assembly axially-integrated normalized pin power range ~0.96–1.05 (~5% radial peaking)
- **Aviles et al. (2017)** — MC21/COBRA-IE companion paper. Source of the 8.7 K spread number.
- **Palmtag (2013)** — CASL-U-2013-0150-001 — original P6 coupled single-assembly. Identified but the public CASL link is dead; reserved for future Body-provided retrieval.

**P6 operating point** (used by `NetflowModelica.Tests.AssemblyVeraP6`, see ADR-0002 + step 1 of the 2026-05-26 unfreeze):
- pellet OD 0.8192 cm; clad OD 0.95 cm; clad ID 0.836 cm (gap 84 µm); pitch 1.26 cm
- active length 365.76 cm; 264 fuel rods + 24 guide tubes + 1 instrument (17×17)
- inlet 565 K; 15.51 MPa; 1300 ppm boron; 3.10 wt% U-235
- assembly power 17.67 MW; 97.4% in fuel; 9% bypass removed
- assembly flow 85.98 kg/s; per-fuel-rod 0.326 kg/s (= 85.98/264)
- average linear heat ~178 W/cm = 17 800 W/m; gap conductance ~7500 W/m²K empirical

## Notes

- **Why no live web sweep:** §2 of CONTEXT.md — priors are stable since 2026-05-21 (Julia closeout); Modelica land does not move fast on stream connectors or IF97 in 5 days. We accept this risk; if a slice trips on a Modelica idiom that turns out to be different from what we remember, the gate fires (Skeptic) and we sweep then.
- **CSL-JSON:** stub-only this round — full bibliographic export would be polish, not load-bearing for a 6-slice dogfood. Re-enable if a publication-quality artifact is later requested.
