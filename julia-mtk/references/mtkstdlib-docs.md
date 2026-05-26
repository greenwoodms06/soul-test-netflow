---
id: mtkstdlib-docs
csl: references.json#mtkstdlib-docs
access: public
retrieved: 2026-05-21
file: none
grounds: [adr-0001, context-prior-art]
key-values:
  - value: "HeatPort = {T [K] across, Q_flow [W] through}"
    defines: "Thermal connector, Modelica-style across/through"
    status: verified
    locus: "API/thermal + connectors/connections docs"
  - value: "Hydraulic = IsothermalCompressible only"
    defines: "p / mass-flow connector; no temperature, enthalpy, or phase"
    status: verified
    locus: "API/hydraulic docs + src tree"
related: [[mtk-jl]]
---

Official SciML standard library for ModelingToolkit. Establishes: the across/through
(potential/flow) connector formalism (confirmed Modelica/SimScape-equivalent); a
lumped Thermal domain (HeatCapacitor, ThermalConductor/Resistor,
ConvectiveConductor/Resistor, BodyRadiation, sources, sensors); and an
isothermal-compressible Hydraulic domain (p/mass-flow only).

What it does NOT establish, and why it matters here: there is **no thermal-fluid /
two-phase / steam / IF97 / Rankine** component. So our `FluidPort` and
`CoolantVolume` (carrying enthalpy) are genuinely custom — confirmed absent, not
overlooked. Reuse Thermal for the radial fuel path; build the fluid transport
ourselves.
