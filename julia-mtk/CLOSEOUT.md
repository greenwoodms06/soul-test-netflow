# CLOSEOUT — soultest-julia (Soul-System dogfood on a Julia/MTK thermal chain)

**Status: COMPLETE / frozen — 2026-05-21.** Successor to the frozen netflow project.

## Purpose (and whether it was met)

This was a **dogfood of the Soul System**, with a bounded Julia/ModelingToolkit
thermal model as the medium. Per the founding handoff, the success metric was **the
process, not the model**: did the Soul gates fire *on their own* this time —
especially the framing/expansion gate forcing the prior-art question up front, and
the completion gate catching overclaims before the Body did?

**Verdict: yes, with one important limit.**
- ✅ The **expansion gate fired before any code** → live prior-art sweep → netflow's
  "Universe Collapse" did **not** repeat.
- ✅ The **completion gate caught a real overclaim** unprompted (the stale
  netflow-README baseline).
- ⚠️ But the completion gate **also passed a Coherent Falsehood** — a wrong
  performance conclusion built on flawed-but-real measurements; only the **Body's
  domain skepticism** caught it. *The gate verifies sourcing, not measurement
  validity.* This is the dogfood's most valuable methodology finding.

## The two deliverables (the actual point)

- **`docs/FINDINGS.md`** — the ledger: **12 MTK capability findings** + **6 Soul
  System findings**. The dogfood's real output.
- **`docs/mtk-experience-report.md`** — curated, send-ready one-pager for the SciML
  team (with figures), pre-empting the obvious rebuttals by having measured them.

### Soul-System findings (headline)
Gate ≠ measurement validity (SOUL-F-a); reaching outward *before* building
repeatedly overturned plans (SOUL-F-f, the MethodOfLines reversal); the
"re-measure, don't trust the record" guardrail paid off ×2; recurring AI failure
mode = **optimistic over-extrapolation**, reliably caught only by anchoring one
point past the claim; and the system is **too verbose** (Body feedback → idea
SJUL-I001, switchable verbosity layers).

### MTK verdict (headline)
Composition (acausal + signal + multiphysics), stream connectors, and **numerics
all work** — Julia matched/beat a hand-rolled sparse solver (1.7× faster @ 10k,
parity @ 90k) and reproduced its physics to 25 mK. The **one real limit is code
generation**: per-component, array-equation, *and* MethodOfLines all scalarize, so
large structured models are compile-bound (~25–40 min for a full assembly). The only
shipping escape, JuliaSimCompiler (IRSystem), is **gated** (JuliaHub registry/license).

## What was built (the medium, all verified)

`test/slice1–10` + `src/ThermalChain.jl`: fuel pin → coolant channel → coupled loop
→ transient → netflow-accuracy match → neutronics+Doppler feedback → momentum/flow
split → multi-pin assembly → axial conduction. `bench/*` = the benchmark + scaling
suite. `docs/` = ADR-0001 (abstraction layer), CONTEXT, BENCHMARK,
performance-comparison, FINDINGS, mtk-experience-report. All physics checked against
analytic invariants or code-comparison; nothing claimed as validated against measured
reality.

## Left open (deliberately not done)

- **JuliaSimCompiler** test (does IRSystem clear the compile wall?) — needs the
  Body's JuliaHub account. *Access-escalation, Body-owned.*
- **Full-TH integration** (momentum + energy + multi-channel flow redistribution in
  one coupled run) — each piece demonstrated separately, not unified.
- Real measured-data validation; two-phase/boiling — out of scope by design.

## What "complete" means here

No further development. The findings are captured and send-ready; the model is a
verified demonstrator. Like netflow, this repo is frozen as a finished artifact — if
the Body resumes (e.g., to test JuliaSimCompiler or send the report), start from
`docs/FINDINGS.md` and this file.
