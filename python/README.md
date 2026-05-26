# netflow

> Generic sparse nonlinear network solver for problems where the physics
> reduce to: nodes hold a state variable, edges relate two endpoints'
> states to a conserved flux, and equilibrium is "sum of edge fluxes at
> each interior node = source."

Status: **v1 in progress.** Core + thermal plugin + transient solver
shipped; layering enforced; 75/75 tests passing. Scales to ~1/8 PWR core
(380k nodes steady; full 17×17 assembly transient in <1 min). Verified
exactly against the textbook fuel-pin closed form; validated at the
integral level against the VERA benchmark — see
[`docs/VALIDATION.md`](docs/VALIDATION.md).

> **Fidelity note.** This is a lumped pre-design scoping tool, honest
> target tens of °C. It is *not* a replacement for CTF/COBRA-TF or
> BISON/FRAPCON. Absolute fuel temperatures depend on the
> `gap_conductance` input (the dominant ±~200 K uncertainty) and the
> supplied power distribution. Read `docs/VALIDATION.md` before trusting
> absolute numbers.

## Why

`netflow` lives between `scipy.sparse` (linear-algebra primitive with no
domain structure) and full-featured domain solvers (SPICE, pandapower,
OpenDSS) that bake their physics in. It competes on cross-domain
genericity and Python ergonomics — *not* on domain depth.

The first concrete plugin is `netflow.thermal`, built for nuclear /
Rankine thermal-hydraulic pre-design: sizing, UA verification, and
bounding heat-transfer calculations that inform or validate against
Modelica/Dymola TRANSFORM models.

## Quick start — thermal

```python
from netflow import Network
from netflow.plugins.thermal import (
    FuelRod, ForcedConvection, CoolPropFluid,
    UO2, Zircaloy4, Helium_gap,
)

net = Network()

# A PWR fuel rod at 18 kW/m
rod = FuelRod(
    r_pellet=4.10e-3, gap_thickness=0.085e-3, r_clad_outer=4.75e-3,
    L=1.0,
    fuel_material=UO2(),
    clad_material=Zircaloy4(),
    gap_material=Helium_gap,
    gap_emissivity=0.85,
    q_lin=18_000.0,
)
ports = rod.build(net, prefix="rod_")

# Pin the clad outer surface to bulk coolant via forced convection
from netflow.core.node import Node
net.add_node(Node(id="coolant", fixed=593.0))   # 320 °C
net.add_edge(ForcedConvection(
    ports.clad_outer, "coolant",
    fluid=CoolPropFluid("Water", default_P=15.5e6),
    mdot=0.30, D_h=12.0e-3, A_ht=3.14e-2,
))

res = net.solve_steady()
print(f"centerline T: {res.states[ports.centerline]:.1f} K")
# centerline T: 1201.9 K
```

See `netflow/plugins/thermal/examples/rankine_pre_design.py` for the
full PWR fuel-pin example with a power sweep.

## Quick start — core (domain-agnostic)

```python
from netflow import Edge, Network, Node

class LinearResistor(Edge):
    def __init__(self, a, b, R):
        super().__init__(a, b); self.R = R
    def flux(self, sa, sb):
        return (sa - sb) / self.R
    def jacobian(self, sa, sb):
        g = 1.0 / self.R
        return (g, -g)

net = Network()
net.add_node(Node(id="hot", fixed=10.0))
net.add_node(Node(id="mid"))
net.add_node(Node(id="cold", fixed=0.0))
net.add_edge(LinearResistor("hot", "mid", R=1.0))
net.add_edge(LinearResistor("mid", "cold", R=1.0))

res = net.solve_steady()
print(res.states["mid"])    # 5.0
```

## Architecture

```
netflow/
  core/                  graph, sparse assembly, Picard + Newton, exceptions
  plugins/thermal/       edges, fluids, materials, components, helpers, examples
  demo/                  trivial linear-resistor plugin used by core tests
  bench/                 scaling benchmarks (10²–10⁴ resistor mesh)
tests/
  core/                  Node/Edge/Network, BC handling, linear/nonlinear
  thermal/               edges, convection (CoolProp), components
  test_layering.py       enforces the core/plugin boundary
docs/superpowers/specs/  design spec for v1
```

### Layering rules (CI-enforced)

- `netflow.core.*` must not import plugins or any domain library.
- Plugins must not reach into private (`_`-prefixed) names of the core.
- Plugins must not reach into other plugins.

The thermal plugin is built atop the *same* public protocol an external
plugin would use. There are no privileged paths.

### Genericity is proven, not claimed

A second plugin, **`netflow.plugins.hydraulic`** (incompressible pipe
networks), was added with **zero changes to `netflow.core`**. It uses a
different state (pressure), a different flux (volumetric flow), and a
genuinely harder nonlinearity than thermal — Darcy-Weisbach
`Q = sign(ΔP)·√(|ΔP|/K)`, whose Jacobian is *singular at zero flow*. It
validates against analytical pipe-flow solutions and a Hardy Cross loop,
including the zero-flow Wheatstone-bridge case. If a third distinct
physics solves on the unchanged core, the core really is domain-agnostic.

```python
from netflow import Network, Node
from netflow.plugins.hydraulic import Pipe

net = Network()
net.add_node(Node(id="A", source=0.5))      # 0.5 m³/s inflow
net.add_node(Node(id="B", fixed=0.0))        # pressure reference
net.add_edge(Pipe("A", "B", K=1e6))          # turbulent pipe
print(net.solve_steady().states["A"])        # junction pressure (Pa)
```

## What ships in v1

**Core**
- `Node`, `Edge` ABC (with optional analytic Jacobian), `Network`,
  `Result`, layered exception types
- Sparse assembly into `scipy.sparse` matrices
- Newton with backtracking damping (default)
- Picard fallback (automatic when any edge lacks `jacobian`)
- Validation: duplicate IDs, missing endpoints, BC contradictions,
  disconnected sub-networks
- Scale validated to 10⁴ nodes in well under 10 s on a laptop

**Thermal plugin**
- Edges: planar/cylindrical conduction (constant k *or* `Material`),
  contact resistance, fouling, UA, gray-body radiation,
  forced convection (Dittus-Boelter, Gnielinski),
  `CoolantAdvection` (upwind enthalpy transport),
  `CoolantMixing` (turbulent lateral mixing)
- Fluids: `CoolPropFluid` (water/steam, R134a, ammonia, …) with a
  quantized linear-interpolation property cache; `CallableFluid` for
  custom or simplified correlations
- Materials catalog: `SS316L`, `Zircaloy4`, `UO2`, `Helium_gap`, `Air`,
  `Constant`; each with documented validity range
- Components: `MultilayerCylindricalWall`, `InsulatedPipeSection`,
  `FuelRod` (with optional empirical `gap_conductance`), `ResistanceStack`
- Helpers: `lmtd`, `effectiveness_ntu`

## Transient (dynamic) solves

The data model carries node `capacity`, and `Network.solve_transient`
integrates `C·dT/dt = F(T, t)` via `scipy.integrate.solve_ivp` (BDF,
stiff). **Pass the analytic sparse Jacobian path** (the framework does
this automatically) — without it, scipy allocates a dense n×n Jacobian
(~15 GB at a full assembly). Time-varying boundary conditions are
supplied through a `source_fn(t, network)` callback.

```bash
# Full PWR-assembly startup transient (cold -> full power over 30 s)
python -m netflow.plugins.thermal.examples.startup_transient \
    --pins 17 --axial 30 --t-end 120 --ramp-end 30 --name-tag pwr17x17
# -> results/startup_assembly_pwr17x17.gif  (animated heatmap)
```

## Scale (measured, not claimed)

Full physics = non-identical radial + cosine axial + solved coolant +
cross-pin mixing. Strictly linear in node count until sparse-LU fill-in
dominates around a few ×10⁵ unknowns:

| Scale | Nodes | Steady solve |
|---|---:|---:|
| 17×17 assembly × 30 axial | 43,928 | ~8 s |
| 50×50 (≈1/8 core) × 30 axial | 380,000 | ~190 s |

The wall is `scipy.sparse` direct factorization, not memory (peaks
~1.8 GB) and not Newton (invariant at ~7 iterations). Beyond ~10⁶
unknowns needs vectorized assembly or an iterative solver — a v2 concern.

## What is explicitly *not* in v1

- Two-phase heat-transfer coefficients (Chen boiling, Nusselt film
  condensation): planned for v2
- Free convection (Churchill-Chu)
- Iterative sparse solvers (GMRES/CG with preconditioner) — direct
  `spsolve` is sufficient at 10⁴ nodes
- Complex / vector state (AC, multi-physics coupling)
- PETSc, cupy, JAX backends
- YAML/JSON declarative front-end
- `pint`/unit checking — **SI by convention** throughout; documented
  in every public docstring

## Installation

```bash
pip install -e .                        # core only
pip install -e ".[thermal]"             # adds CoolProp for the thermal plugin
pip install -e ".[thermal,viz,dev]"     # everything
```

Requires Python ≥ 3.11.

## Tests and benchmarks

```bash
pytest                                                  # full suite (~1 s)
python -m netflow.bench.resistor_mesh                   # scaling benchmark
python -m netflow.plugins.thermal.examples.rankine_pre_design
```

## Design philosophy

This project is built under [the Soul System](../Soul-System) — a
collaborative methodology that demands the abstraction layer be named
explicitly *before* implementation. The full design spec, including the
"what varies / what decides / what cannot vary" decomposition, lives in
`docs/superpowers/specs/2026-05-19-netflow-design.md`. Read it before
proposing structural changes.
