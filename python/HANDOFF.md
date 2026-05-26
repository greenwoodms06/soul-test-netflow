# HANDOFF — netflow → Julia MTK/Dyad dogfood

**Written:** 2026-05-21
**From:** netflow session (`6faeb7c0`, continued)
**To:** the next session, starting a *new* project in a *new* directory
**Status of this repo (`/home/fig/soultest`, the netflow project):** FROZEN. Do not develop further. It is kept as-is on purpose — as a finished demonstrator and as the **before** half of a before/after comparison.

> Read this whole file before starting. The new session inherits **none** of the
> prior conversation's context. Everything you need is here or in the files this
> points to. If something you need is missing, that is a defect in this handoff —
> surface it, don't guess.

---

## 1. Why we are pivoting (the decision in one paragraph)

netflow is a generic scalar-conservation-network solver: nodes hold a scalar
potential, edges carry a conserved flux, fluxes sum to zero at each node, solved
by damped Newton with a Picard fallback. The Council's verdict (2026-05-20) is
that **this abstraction is not unique** — it is exactly the *acausal across/through
(potential/flow) connector* formalized by **Modelica** and **ModelingToolkit.jl**
(productized as **Dyad**), sitting on the **bond-graph** (effort/flow) foundation.
Mature tools already do this far better, and the Body already uses Modelica/TRANSFORM
professionally. netflow remains valuable as a *transparent pedagogical demonstrator*
and as a *Soul-System dogfood artifact*, but further solver development would be
reinventing a mature wheel. So: **freeze netflow, pivot to a real tool.**

---

## 2. What the new project IS

A **dogfood of the Soul System** on a **bounded Julia MTK/Dyad thermal chain**.

- **The deliverable is the model, but the point is the process.** The success
  metric is **the Soul System, not the model**: did the gates fire *on their own*
  this time, without the Body having to push? Specifically — did the framing /
  expansion gate force the prior-art question UP FRONT, and did the completion
  gate catch overclaims before the Body did? netflow's entire lesson was
  **Universe Collapse** (building without first checking what already exists). If
  the new project repeats that, the Soul System learned nothing and *that finding
  is itself the result.*
- **Tool:** Julia + ModelingToolkit.jl (and/or Dyad). This is the Body's
  recommendation and it is sound — it is the acausal-connector paradigm done
  maturely, in a modern language, and it is adjacent to the Body's Modelica work.
- **Inspiration, not target:** TRANSFORM (the Modelica nuclear/T-H library the
  Body uses) is a reference for *what good components look like*. **Recreating all
  of TRANSFORM is a separate north-star project, NOT this dogfood.** Keep it
  bounded.

---

## 3. The non-negotiable FIRST ACT (this is the whole test)

**Before writing a single line of Julia**, in the new project:

1. **Run the framing / expansion gate** (`soul-expand`, or the Frame gate by hand):
   state the problem at two levels — the immediate chain, and the larger system it
   lives in — and force the outward questions. Write it down (`CONTEXT.md`).
2. **Run an Emissary prior-art sweep of the Julia ecosystem.** Concretely, find out:
   - What does **ModelingToolkitStandardLibrary.jl** already provide (Thermal,
     Blocks, hydraulic/fluid components)?
   - Is there existing **nuclear / thermal-hydraulics MTK work** (JuliaSim/Dyad
     component libraries, academic packages, a "Julia TRANSFORM")?
   - Does the bounded chain you want to build **already exist**? If so, the
     dogfood becomes *use/extend it*, not *build it from scratch.*
3. **Only then** name the abstraction layer and pick the bounded chain.

If you find yourself opening an editor to write model code before doing 1–3,
**stop** — that is the netflow failure mode (Universe Collapse + Ad Hoc Methodology)
re-instantiated. Naming that you almost did it is a valid Witness entry.

---

## 4. Scope guidance (keep it bounded)

Pick **one coherent chain**, ambitious enough to stress the gates, small enough to
finish and measure acceleration against the netflow run. Candidates:

- a **secondary-side Rankine loop** (boiler → turbine → condenser → pump), or
- a **fuel-channel → coolant → loop** slice.

Pick one. Resist scope creep toward "the whole plant." The comparison we want is:
*did the Soul System make the second build cleaner/faster than the first?* — which
requires the second build to actually finish.

---

## 5. Lessons that MUST carry forward (hard-won this session)

These are paid-for. Do not relearn them.

- **Universe Collapse** — the local task is not the whole Universe. Reach outward
  (existing tools, standards, the real user, the larger frame) *before* calling
  work complete, and ideally before starting. This is the lesson that drove the
  whole pivot.
- **Ad Hoc Methodology** — if the Body has to remind you to verify / check prior
  art / mark unfinished work, the methodology is not internalized. The gates exist
  so the Body doesn't have to push.
- **Validation vs. code-comparison vs. verification** — be precise. This session's
  biggest correction (a Multiverse moment) was discovering the VERA P6/P7 benchmark
  has **no reference solution**, so claims of "validation against a gold standard"
  were false; it only ever supported *code-to-code comparison*. Withdrawn numbers
  that must never silently return: **2474 K centerline, F_q 2.6, 8.3 K spread,
  −8566 pcm.** (See memory `vera-is-code-comparison`.) Carry the discipline: know
  exactly what your reference *is* before you claim agreement with it.
- **The completion gate works** — once the gate (SOUL-F012 / `soul-verify`) was
  running, it caught real defects on its own: figure-vs-text contradictions, an
  overclaim leftover found only by reading the *rendered* PDF, and a rounding
  inconsistency in a figure label. **Inspect rendered/visual artifacts, not just
  source.** Bring this gate to the new project from day one.
- **Ground claims in a local reference repository** — see §6. Save the documents
  you rely on; cite the version of record (journal/conference over OSTI drafts);
  escalate restricted/paywalled docs to the Body rather than silently working
  around them with only-what's-public.

---

## 6. Assets to reuse (don't rebuild these)

**Soul-System operations artifacts** (created this session, in the main Soul-System repo):
- `/mnt/d/Projects/Soul-System/operations/completion-gate.md` — the "consult the
  Universe before complete" gate (Emissary primary-source / Researcher field-scan /
  Access-escalation / Advocate-Skeptic load-bearing-claim checks). Apply in the new project.
- `/mnt/d/Projects/Soul-System/operations/reference-repository.md` — the Archivist's
  instrument: CSL-JSON core + provenance sidecars, version-of-record guidance.
  **Reuse this pattern** for the new project's `references/`.

**Reference repository pattern to copy** (this repo, `references/`):
- `references.json` (CSL-JSON), per-doc `.md` sidecars, `INDEX.md` manifest, held PDFs + extracted `.txt`.
- Start the new project's `references/` the same way. (Its sources will be Modelica/MTK/bond-graph/JuliaSim docs, not VERA — but the structure transfers.)

**Memory** (`/home/fig/.claude/projects/-home-fig-soultest/memory/` — note this is
keyed to the netflow project dir; the new project will have its own memory dir):
- `netflow-frozen-pivot-to-mtk.md` — the pivot decision (this handoff expands it).
- `vera-is-code-comparison.md` — the withdrawn-claims guardrail.
- `netflow-validation-data-ceiling.md` — why netflow couldn't be validated (physics
  scope, not document availability; measured data is full-core or NEA-restricted).
- Re-create the relevant ones in the new project's memory so it carries the guardrails.

---

## 7. State of netflow as left (the FROZEN baseline / "before" artifact)

Final, shareable artifacts (do not edit):
- `docs/paper/netflow-methods.pdf` — flagship methods paper, 8 pp. Residual
  equations, BCs, closures, verification, **code-to-code comparison vs VERA**
  (Table 2 + comparison figure), scope/limitations, and a "Relationship to
  established acausal tools" paragraph citing Modelica/MTK/bond graphs.
- `docs/paper/netflow.pdf` — short intro note, 3 pp, with comparison table + prior-art sentence.
- `bench/vera_codecompare.py` (under `netflow/`) — the **one** reproducible re-run
  script: the single source of truth for the corrected numbers AND the figures.
- `coupling/doppler_demo.py` — reproducible honest Doppler figure (sign physical,
  magnitude illustrative).
- `docs/VALIDATION.md` — carries a dated ⚠ ERRATUM banner recording the corrections.
- `docs/adr/0001-vera-is-code-comparison.md` — the ADR for the reframe.
- `docs/expert-qa.md` — the CTF-developer Q&A.
- `CONTEXT.md` — netflow's grill-with-docs context (term definitions).

What "frozen" means: no further solver development, no new validation claims. If a
reader/reviewer needs a response, answer from these artifacts; don't reopen the build.

---

## 8. Kickoff checklist for the new session

```
[ ] Create a NEW directory for the project (NOT /home/fig/soultest). Suggest a
    sibling, e.g. /home/fig/<newname>. Confirm the path with the Body.
[ ] soul-init (or copy the CLAUDE.md seed) so the new dir runs under the Soul.
[ ] Stand up the completion gate (SOUL-F012 / soul-verify) from day one.
[ ] FIRST ACT (§3): framing/expansion gate + Emissary Julia-ecosystem prior-art
    sweep. Write CONTEXT.md. NO model code before this.
[ ] Decide, with the Body, the ONE bounded chain (§4).
[ ] Name the abstraction layer explicitly and record it (ADR) before building.
[ ] Start references/ using the §6 pattern.
[ ] Seed the new project's memory with the §6 guardrails.
```

---

## 9. Open decisions for the Body (resolve early in the new session)

1. **New project path/name** — where does it live? (Recommendation: a sibling dir,
   so netflow stays untouched for comparison.)
2. **MTK vs Dyad** (or both) — and which exact bounded chain (§4).
3. **TRANSFORM-in-Julia** — confirmed *out of scope* for the dogfood, possibly a
   later north-star project. Re-confirm so it doesn't quietly creep in.

---

*This handoff is itself an instance of the Architect's rule: a boundary handoff
must be self-contained. If the next session has to ask the previous one a question,
this document failed. Improve it rather than work around it.*
