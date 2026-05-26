---
id: ai4e-componentlib
csl: references.json#ai4e-componentlib
access: public
retrieved: 2026-05-21
file: none
grounds: [adr-0001, context-prior-art]
key-values:
  - value: "last push 2024-07-16, 33 stars"
    defines: "activity/maturity at sweep time"
    status: verified
    locus: "GitHub repo metadata"
  - value: "quasi-static state-point analysis (IsobaricProcess, IsentropicProcess, ... + CoolProp)"
    defines: "architecture — process blocks, NOT dynamic equipment with balances"
    status: verified
    locus: "src/lib/ThermodynamicCycle/components/{process.jl,states.jl}"
related: [[mtk-jl]]
---

The closest existing Julia/MTK power-cycle code found in the 2026-05-21 sweep. It
has runnable Rankine/Brayton examples on MTK + CoolProp, BUT it is dormant and
architecturally **quasi-static** — thermodynamic *process* blocks over state nodes,
not first-class equipment components (no Turbine/Boiler/Pump types with mass/energy/
momentum balances). It does NOT turn this project into use/extend; at most it is a
reference for wiring MTK to a property backend. Recorded so the "build vs use/extend"
decision stays auditable.
