# netflow

A generic solver for problems reducible to **conservation of a scalar flux at the
nodes of a network**. One domain-agnostic core hosts physics (thermal, hydraulic,
neutronic) as plugins.

## Language

**Network**:
The solved object — nodes joined by edges, over which a scalar flux is conserved.

**Node**:
Carries one scalar **state** (temperature, pressure, neutron flux). *Interior* (an
unknown) or *Dirichlet* (fixed/boundary).
_Avoid_: vertex, bus.

**Edge**:
Relates its two endpoint node states to a conserved **flux** `f(s_a, s_b)`. All
physics enters here.
_Avoid_: link, branch, resistor.

**Flux**:
The conserved quantity an edge carries — heat rate (W), volumetric flow (m³/s),
neutron leakage. Conservation of flux at every interior node is the residual.
_Avoid_: current, rate.

**Driven solve**:
Solving `F(x)=0` for a network with fixed sources and boundaries. The core's only
operation.
_Avoid_: forward solve.

**Outer loop**:
Repeated driven solves that express a larger problem *structure* — transient
(time stepping), eigenvalue (power iteration), coupled multiphysics (Picard).
_Avoid_: iteration (ambiguous).

**Plugin**:
A domain supplying edge flux functions only. Imports the core; never another
plugin.
_Avoid_: module.

**Coupling layer**:
Code that orchestrates several plugins (and may import several). Sits above
plugins.

**Verification**:
Evidence the equations are solved *correctly* — vs analytic/closed forms, machine
precision, convergence order. Internal.
_Avoid_: validation, testing, benchmarking.

**Validation**:
Evidence the equations match *reality* — vs measured data. Needs the Universe.
_Avoid_: verification, benchmarking.

**Code comparison**:
Agreement with *another code's* solution — not reality. This is what VERA P6/P7
support (they have no reference solution).
_Avoid_: validation.

## Relationships

- A **Network** is composed of **Nodes** joined by **Edges**.
- Each **Edge** computes a **Flux** from two **Node** states; conservation of flux
  at interior nodes is the residual the **Driven solve** zeroes.
- A **Plugin** supplies **Edge** types; the **Coupling layer** combines **Plugins**.
- An **Outer loop** drives repeated **Driven solves**.
- **Verification** is internal; **Validation** reaches the Universe (measured data);
  **Code comparison** sits between — another code's answer, not reality.

## Example dialogue

> **Dev:** "We validated the fuel temperature against VERA."
> **Domain expert:** "VERA P6/P7 have no reference solution — you compared against
> CTF's *answer*. That's a code comparison, not validation. And which temperature?
> You computed centerline; CTF reports volume-average. Compare like for like."

## Flagged ambiguities

- "validation" was used for what was actually **verification** (analytic) and
  **code comparison** (vs CTF) — resolved: three distinct terms above; VERA P6/P7
  supports only **code comparison** (see ADR-0001).
- "fuel temperature" was used for *centerline* when the comparison source reports
  *volume-average* — resolved: always state which quantity.
