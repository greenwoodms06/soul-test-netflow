---
id: dyad-faq
csl: references.json#dyad-faq
access: public
retrieved: 2026-05-21
file: none
grounds: [adr-0001, context-tool-decision]
key-values:
  - value: "source-available, NOT open source"
    defines: "compiler license (community-reported modified PolyForm-Strict); std libs BSD-3"
    status: verified
    locus: "Dyad FAQ + Discourse"
  - value: "distributed via closed DyadRegistry, requires free JuliaHub account"
    defines: "access gate — not in the Julia General Registry"
    status: verified
    locus: "Dyad FAQ + installation docs"
related: [[mtk-jl]]
---

Grounds the tool decision (CONTEXT.md §6): Dyad is runnable for free for personal/
non-commercial use, but it is vendor-gated (JuliaHub account + closed registry),
its standard libraries cover the *same* thermal/hydraulic domains as MTKStdLib (no
Rankine/thermal-fluid head start), and it lowers to MTK anyway. → plain MTK chosen;
the Dyad upgrade path stays open. Exact compiler license terms are community-reported,
not read from the LICENSE file — re-verify before any commercial/government use.
