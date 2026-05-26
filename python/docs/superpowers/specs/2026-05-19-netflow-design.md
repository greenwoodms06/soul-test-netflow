# netflow — Design Spec

**Status:** approved-in-brainstorm, awaiting implementation
**Date:** 2026-05-19
**Authors:** greenwoodms06, Claude (under the Soul System)
**Tentative package name:** `netflow` (provisional — see Naming, §11)

---

## 1. Purpose at Two Levels

### 1.1 Immediate problem
A Python framework that builds an arbitrary network of nodes and edges, where each edge expresses a *flux* as a (possibly nonlinear) function of its two endpoints' *states*, and solves the network at steady state under mixed Dirichlet/Neumann boundary conditions. Designed so adding lumped capacitance for transient solves is a clean future extension, not a rewrite.

### 1.2 Larger system
A generic core for massive-sparse nonlinear network problems where the underlying math is conservation at nodes + a flux law on edges. The first concrete application is nuclear/Rankine thermal-hydraulic pre-design and sanity-checking — building lumped thermal resistance networks to size, verify UA, and bound heat-transfer estimates ahead of (or alongside) Dymola/TRANSFORM Modelica modeling. Thermal becomes a *plugin* on the generic core. Future plugins (electrical, hydraulic, neural) are peers of thermal, not afterthoughts.

The framework occupies a niche between `scipy.sparse` (linear-algebra primitive, no domain structure) and full-featured domain solvers (SPICE, pandapower, OpenDSS). It does not attempt to compete with domain depth — it competes on cross-domain genericity and Python ergonomics.

---

## 2. Abstraction Layer (the load-bearing wall)

### 2.1 What varies
- Domain (which plugin)
- State variable per node (v1: scalar real; future: complex, vector)
- Edge primitive `f(state_a, state_b, params) → flux` and optional analytic Jacobian
- Linearity — purely linear, weakly nonlinear (Picard), strongly nonlinear (Newton)
- Solver — direct sparse (SuperLU via `scipy.sparse.linalg.spsolve`) in v1; iterative deferred
- Boundary conditions — Dirichlet (fixed state), Neumann (fixed source/flux into node)
- Future: time (transient via `solve_ivp` / IMEX), backend (PETSc, cupy)

### 2.2 What decides whether it varies
- Scale → selects solver (only direct in v1)
- Domain physics → state type, edge linearity, Jacobian availability
- Whether the user requests transient (not in v1)

### 2.3 What cannot vary
- KCL/conservation at every interior node: `source_i + Σ flux_in − Σ flux_out = 0`
- Edge protocol: two endpoints + parameters → scalar flux (+ optional `(∂f/∂a, ∂f/∂b)`)
- Sparse representation throughout — no dense Jacobians at scale
- BC mechanism: Dirichlet eliminated from unknowns; Neumann adds to RHS
- Solver returns the unknowns *plus* residual history, iteration count, convergence flag — never just "the answer"
- Core has zero domain imports (enforced by an import-lint test in CI)

---

## 3. Architecture

```
netflow/
├── core/                         core — zero domain imports
│   ├── network.py                Network: container, validation, solve entry points
│   ├── node.py                   Node: id, state (unknown), Dirichlet, Neumann, optional C
│   ├── edge.py                   Edge ABC: flux(); optional jacobian()
│   ├── assembly.py               residual & jacobian assembly into scipy.sparse
│   ├── solver.py                 SteadySolver: Picard, Newton-with-damping; convergence
│   ├── result.py                 Result: states, edge fluxes, residual history, converged, n_iter
│   └── exceptions.py             SingularJacobian, DisconnectedGraph, NonConvergence, BadBC
│
├── plugins/
│   └── thermal/                  netflow.thermal — first real plugin
│       ├── edges/
│       ├── fluids.py
│       ├── materials.py
│       ├── components/
│       └── examples/             Rankine pre-design walkthrough
│
├── demo/                         resistor mesh / scalar diffusion — used by tests
├── bench/                        scaling benchmarks 10²–10⁴
├── tests/
└── docs/
```

**Dependency stack:** `numpy`, `scipy`. Thermal plugin adds `CoolProp`. `networkx` optional (visualization only, never on the hot path). No JAX, no PETSc, no `pint` in v1.

**Layering rules (CI-enforced):**
- `netflow.core.*` must not import `netflow.plugins.*` or any domain library.
- Plugins must not access private names in `netflow.core` (the `_nodes`, `_edges`, index maps, etc.).
- Plugins must work via the same public protocol an external plugin would use.

---

## 4. Core Data Model

### 4.1 Node
```python
@dataclass
class Node:
    id: str
    fixed: float | None = None       # Dirichlet
    source: float = 0.0              # Neumann (+ into node)
    capacity: float | None = None    # stored for transient; ignored at SS
    state0: float = 0.0              # initial guess
    meta: dict = field(default_factory=dict)
```
Node IDs are strings (survive renaming, serialization, subgraph merging). Internal int indexing is an assembly detail, not API.

### 4.2 Edge
```python
class Edge(ABC):
    """Edge a→b. Sign convention: positive flux is transport from a to b."""
    def __init__(self, a: str, b: str):
        self.a = a
        self.b = b

    @abstractmethod
    def flux(self, state_a: float, state_b: float) -> float: ...

    def jacobian(self, state_a, state_b) -> tuple[float, float] | None:
        return None
```
Edges don't carry a Network reference. They reference endpoints by ID; the Network validates on `add_edge`.

### 4.3 Network
```python
class Network:
    def add_node(self, node: Node) -> Node: ...
    def add_edge(self, edge: Edge) -> Edge: ...
    def merge_subgraph(self, nodes, edges, prefix="") -> dict[str, str]: ...
    def validate(self) -> ValidationReport: ...
    def solve_steady(self, *, method="newton", tol=1e-8, max_iter=50,
                     damping=1.0, raise_on_nonconverge=False) -> Result: ...
    # Reserved (not v1): solve_transient(t_span, y0=None, **opts)
```

### 4.4 Result
```python
@dataclass
class Result:
    states: dict[str, float]
    edge_fluxes: list[float]
    converged: bool
    n_iter: int
    residual_history: np.ndarray
    method: str
    elapsed_s: float
    def state_array(self) -> np.ndarray: ...
    def edge_flux(self, edge: Edge) -> float: ...
```

---

## 5. Solver Pipeline

**Indexing.** `solve_steady()` partitions nodes into interior (unknowns) and Dirichlet (fixed), builds a `node_id → row_index` map for interior nodes, and freezes for the duration of the solve.

**Residual.** For interior node *i*:
```
F_i(x) = source_i  +  Σ_{e=(a,b), b==i} f_e(x_a, x_b)  −  Σ_{e=(a,b), a==i} f_e(x_a, x_b)
```
`x_a`, `x_b` come from `x` (if interior) or `node.fixed` (if Dirichlet).

**Jacobian.** Assembled from per-edge COO triplets. Edges without `jacobian()` cause an automatic Picard fallback (logged).

**Newton with backtracking damping** (default):
```
while ||F||_inf > tol and k < max_iter:
    solve J·δ = -F   (scipy.sparse.linalg.spsolve)
    α = 1.0
    while ||F(x + α·δ)||_inf > ||F(x)||_inf and α > α_min:
        α /= 2
    x ← x + α·δ
    record (||F||, α, k)
```

**Picard fallback.** Computes effective conductance `g_e = f_e/(x_a − x_b)` (with small-denominator guard, returning the linear-limit slope from `jacobian()` if available, else a finite-difference estimate), assembles a linear Laplacian, solves, repeats.

**Convergence.** `tol = 1e-8` on `||F||_inf`, `max_iter = 50`. On non-convergence, returns `Result(converged=False, …)` by default. Strict mode raises `NonConvergence`.

**Singular Jacobian.** Raised with the offending row index — usually an interior node disconnected from any Dirichlet path.

---

## 6. Plugin Protocol

A plugin is a Python module that subclasses `Edge` (and optionally provides Components).

**Plugin contract:**
- Edge subclasses implement `flux()`; *should* implement `jacobian()`. Omission → silent Picard downgrade (logged once per solve).
- Plugins import only from `netflow.core` (and their own third-party deps).
- Components have `build(network, prefix="") -> Ports` semantics. `Ports` is any small dataclass exposing named node-id strings.

**Enforcement.** A CI test imports `netflow.thermal` and asserts it does not reference any name in `netflow.core` starting with `_`. If the plugin needs something private, that's a signal to promote it.

---

## 7. Thermal Plugin (v1)

### 7.1 Edges
| Class | Linearity | Jacobian | Notes |
|---|---|---|---|
| `PlanarConduction(L, k, A)` | linear if `k` is float; nonlinear if `Material` | analytic | `R = L/(kA)`. `k` accepts `float` *or* `Material`. |
| `CylindricalConduction(r_i, r_o, L, k)` | linear if `k` is float; nonlinear if `Material` | analytic | `R = ln(r_o/r_i)/(2πLk)`. `k` accepts `float` *or* `Material`. |
| `ContactResistance(R)` | linear | analytic | constant |
| `Fouling(Rf, A)` | linear | analytic | `R = Rf/A` |
| `UAEdge(UA)` | linear | analytic | scalar UA |
| `Radiation(emissivity, area, view_factor=1.0)` | nonlinear (T⁴) | analytic | gray-body |
| `ForcedConvection(fluid, mdot, D_h, A, length, correlation)` | nonlinear (props vary with film T) | Picard in v1 | DB or Gnielinski |

When a conduction edge is constructed with `k = some_Material`, the edge becomes nonlinear: flux uses `k(T_mean)` evaluated at the mean of the two endpoint temperatures, and the jacobian carries both the conductance term and the sensitivity `∂k/∂T · ½` contribution at each endpoint (central-difference approximation if `Material` does not expose an analytic derivative).

### 7.2 Fluids
```python
class Fluid(ABC):
    @abstractmethod
    def rho(self, T, P): ...
    @abstractmethod
    def mu(self, T, P): ...
    @abstractmethod
    def k(self, T, P): ...
    @abstractmethod
    def cp(self, T, P): ...
    def Pr(self, T, P):
        return self.mu(T, P) * self.cp(T, P) / self.k(T, P)
```
- `CoolPropFluid(name="Water", P=...)` — default; wraps `CoolProp.PropsSI`
- `CallableFluid(rho=..., mu=..., k=..., cp=...)` — escape hatch

### 7.3 Materials
```python
class Material(ABC):
    @abstractmethod
    def k(self, T) -> float: ...
```
Catalog: `SS316L`, `Zircaloy4`, `UO2`, `Helium_gap`, `Air`, `Constant(k=...)`. Each carries a documented validity range and raises a `RangeWarning` outside it.

### 7.4 Components
| Component | Ports | Purpose |
|---|---|---|
| `MultilayerCylindricalWall(layers, L, r_inner)` | `.inner`, `.outer`, `.interface(i)` | Multi-layer pipe walls |
| `InsulatedPipeSection(...)` | `.bore`, `.ambient` | Sugar over MultilayerCylindricalWall |
| `FuelRod(r_pellet, gap, r_clad_outer, L, fuel_mat, clad_mat, gap_emissivity, q_lin)` | `.centerline`, `.pellet_surface`, `.clad_inner`, `.clad_outer` | Pellet conduction + parallel gap conduction/radiation + clad conduction + linear-power Neumann source. The model that exercises every nonlinear path in v1. |
| `ResistanceStack(*resistances)` | `.upstream`, `.downstream` | Generic series builder |

### 7.5 Helpers (not edges)
- `lmtd(Th_in, Th_out, Tc_in, Tc_out)` — HX post-processing against `UAEdge`
- `effectiveness_ntu(...)` — same role

### 7.6 Explicitly *not* v1
- `CounterFlowHX` as a component (LMTD/NTU-ε is post-processing, not a graph edge — folding it into a "component" would smuggle a multi-edge stream model into the resistance abstraction)
- Two-phase HTCs (Chen, Nusselt condensation, …)
- Free convection (Churchill-Chu)

---

## 8. Validation & Testing

### 8.1 Unit tests
- Every edge: analytical R verification at known operating points
- Every edge with `jacobian()`: agreement with central finite difference to rtol ≤ 1e-6

### 8.2 Integration — analytical benchmarks
1. Multilayer planar wall → series-sum closed form
2. Multilayer cylindrical wall → log series
3. Concentric-cylinder radiation (Incropera Ex.)
4. 1-D fin discretized into N nodes → mesh-refinement study against fin equation
5. FuelRod with linear power → analytical pellet centerline T
6. 3-surface radiation enclosure → nonlinear solver shakedown

### 8.3 Scaling benchmarks (`bench/`)
- 2D resistor mesh, 10×10 → 100×100
- Time `solve_steady()`; memory profile; Newton vs Picard iteration counts
- Target: 10⁴ nodes in well under 10 s on a laptop. Failure to hit this becomes a documented limitation, not a silent regression.

### 8.4 Stress tests
- Disconnected sub-network → `DisconnectedGraph`
- All-Dirichlet network → noop with consistency check
- Singular Jacobian → meaningful error, offending row identified
- Deliberate Newton divergence → `Result.converged=False` returned, never silently wrong

### 8.5 Layering linter
Test that asserts `netflow.thermal` references no `_`-prefixed name in `netflow.core`. Run in CI.

---

## 9. Out of Scope for v1

- Transient solver (data model carries `capacity` already — extension only)
- Two-phase HTCs
- Free convection
- Iterative sparse solvers (GMRES / CG with preconditioner) — direct `spsolve` is fine at 10⁴
- Complex / vector state (AC, multiphysics)
- PETSc, cupy, JAX backends
- YAML/JSON declarative front-end
- `pint` / unit checking — SI by convention, documented in every public docstring
- GUI / interactive visualization beyond a `to_networkx() → matplotlib` helper

---

## 10. Failure Modes the Soul Names (and how this design avoids them)

| Failure mode | Mitigation in this design |
|---|---|
| **Premature Sophistication** | v1 ships only direct sparse + Picard/Newton. No iterative solvers, no JAX, no PETSc until a real workload demands them. |
| **Premature Deferral** | The transient extension hook (`capacity` field, `solve_transient` signature reserved) is *defined now* because we already know transient is wanted. Not built — but not blocked-on either. |
| **Defaulting to Instantiation** | Core has zero domain imports; the abstraction layer is enforced by CI. The thermal plugin is built atop the same public surface any future plugin would use. |
| **Partial Domain Coverage** | v1 covers conduction + UA + radiation + contact/fouling + forced convection — the spread that exercises linear, nonlinear, and property-dependent edges. Two-phase explicitly deferred with a named criterion (a v2 release). |
| **Ad Hoc Methodology** | This spec is the methodology. Implementation stages flow from it, each with its own test gate. |

---

## 11. Naming

`netflow` is provisional. The name conflicts with NetFlow protocol tooling and may need a public-release rename. Candidates: `thermflow`, `restorch`, `nodalflux`, `pynetres`, `gridkit`. **Action item:** confirm name before any public release; safe to use `netflow` internally during v1 development.

---

## 12. Open Items for Implementation Stage

These are decisions deliberately left to implementation, surfaced here so they're not forgotten:

1. **Logging.** Standard `logging` module, namespaced `netflow.*`. Solver iteration history at INFO, per-edge dispatches at DEBUG.
2. **Public vs private surface.** Public re-exports in `netflow/__init__.py` will be enumerated explicitly (no wildcard imports).
3. **Material/fluid range warnings.** Use `warnings.warn(RangeWarning, …)` with stacklevel so the user sees their own call site.
4. **Result mutation.** Result objects are immutable (`frozen=True` dataclass) — solving twice returns two Results.
5. **Seeding.** Initial guesses default to the mean of Dirichlet values for connected interior nodes. Bad guess + nonlinear edges + no damping is the most common user error; the default damping policy mitigates it.
