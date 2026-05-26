# References — manifest

One line per reference. Bibliographic core in `references.json`; provenance in
per-slug `.md` sidecars. Seeded from the 2026-05-21 prior-art sweep (see memory
`prior-art-julia-thermal-mtk`). All entries are currently `access: public`,
web-retrieved; no PDFs held yet — a source becomes file-held the moment it is
cited for a load-bearing number.

- **mtkstdlib-docs** — MTKStandardLibrary docs; the connector contract + Thermal/
  Hydraulic component inventory we build on. [sidecar]
- **mtk-jl** — ModelingToolkit.jl itself (the engine).
- **ai4e-componentlib** — closest Julia prior art; dormant, quasi-static; wiring
  reference only, NOT a use/extend target. [sidecar]
- **dyad-faq** — Dyad licensing/access (why we chose plain MTK over Dyad). [sidecar]
- **thermopower** — Modelica reference for component contracts (design inspiration).
- **clapeyron-jl** — pure-Julia EoS incl. IAPWS-95 (candidate property backend).
- **coolprop-jl** — full IF97 wrapper (candidate property backend).
- **steamtables-jl** — pure-Julia IF97 (candidate property backend).
