"""Realistic scaling benchmark: axially-discretized PWR fuel pins.

The scale ladder probes where per-edge Python dispatch (the ergonomic
choice in v1) becomes the wall.

Single pin model per axial slice:
    centerline ── pellet_conduction ── pellet_surface ── (gap_cond || rad) ──
        clad_inner ── clad_conduction ── clad_outer ── forced_convection ── coolant_i

Axial coupling: small UA between adjacent slices at the clad-outer node
(representing rod-structural axial conduction).

Coolant: each axial slice gets its own Dirichlet temperature; values
follow an enthalpy-rise calculation from the inlet up the channel.

Run:

    python -m netflow.bench.fuel_array              # default ladder
    python -m netflow.bench.fuel_array --max-pins 17 --axial 30 --plot
"""

from __future__ import annotations

import argparse
import math
import pathlib
import time
from dataclasses import dataclass

from netflow import Network
from netflow.core.node import Node
from netflow.plugins.thermal import (
    CoolantAdvection,
    CoolantMixing,
    CoolPropFluid,
    ForcedConvection,
    FuelRod,
    Helium_gap,
    UAEdge,
    UO2,
    Zircaloy4,
)


# ---------------------------------------------------------------------------
# Geometry / operating point — fixed PWR-ish values
# ---------------------------------------------------------------------------

R_PELLET = 4.10e-3
GAP_THICKNESS = 0.085e-3
R_CLAD_OUTER = 4.75e-3
PITCH = 12.6e-3
ROD_OD = 2 * R_CLAD_OUTER

P_SYSTEM = 15.5e6        # Pa
MDOT_CHANNEL = 0.30      # kg/s per subchannel
T_COOLANT_INLET = 565.0  # K (292 °C)
Q_LIN_NOMINAL = 18_000.0 # W/m


# ---------------------------------------------------------------------------
# Coolant axial temperature profile (precomputed enthalpy rise)
# ---------------------------------------------------------------------------

def coolant_axial_temps(
    n_axial: int, slice_L: float, q_lin,
    T_inlet: float = T_COOLANT_INLET,
    mdot: float = MDOT_CHANNEL,
    cp_avg: float = 5500.0,    # rough avg for sub-cooled water @ 15.5 MPa
    axial_shape: "Callable[[float], float] | None" = None,
) -> list[float]:
    """Approximate bulk coolant T at the *midpoint* of each axial slice.

    Parameters
    ----------
    q_lin :
        Float (constant axial profile) OR callable q(z_norm) → q_lin
        where z_norm = (k + 0.5)/n_axial ∈ (0, 1). When ``axial_shape``
        is supplied, q_lin is taken as the *average* and the shape
        scales it per slice.
    axial_shape :
        Optional axial multiplier; if given, q(k) = q_lin · shape(z_norm).
        ``cosine_axial_shape(peak_factor)`` returns a suitable callable.
    """
    Ts: list[float] = []
    cumulative_Q = 0.0
    for i in range(n_axial):
        z_norm = (i + 0.5) / n_axial
        if axial_shape is not None:
            q_here = (q_lin(z_norm) if callable(q_lin) else q_lin) * axial_shape(z_norm)
        else:
            q_here = q_lin(z_norm) if callable(q_lin) else q_lin
        # Half-slice rise on each side: bulk T at midpoint =
        #   T_inlet + (upstream slices' Q + half this slice's Q) / (mdot·cp)
        upstream_Q = cumulative_Q + 0.5 * q_here * slice_L
        Ts.append(T_inlet + upstream_Q / (mdot * cp_avg))
        cumulative_Q += q_here * slice_L
    return Ts


def cosine_axial_shape(peak_factor: float = 1.5):
    """Standard chopped-cosine axial power shape.

        q(z_norm) = 1 + (peak_factor − 1) · cos(π · (2 · z_norm − 1))

    * Peak at z_norm = 0.5 → ``peak_factor``
    * Min  at z_norm = 0, 1 → ``2 − peak_factor``
    * Integral over [0, 1]  = 1 (so average is preserved)

    Domain: ``peak_factor ∈ [1, 2]`` (above 2 the ends would go
    negative; clip at 2 if a sharper profile is desired in v2).
    """
    if not (1.0 <= peak_factor <= 2.0):
        raise ValueError("peak_factor must be in [1, 2]")

    def shape(z_norm: float) -> float:
        return 1.0 + (peak_factor - 1.0) * math.cos(math.pi * (2 * z_norm - 1))
    shape.peak_factor = peak_factor   # type: ignore[attr-defined]
    return shape


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _add_axial_pin(
    network: Network,
    *,
    pin_id: str,
    n_axial: int,
    slice_L: float,
    q_lin_per_slice: list[float],
    coolant_Ts: list[float],
    coolant: CoolPropFluid,
    subchannel_A_xs: float,
    subchannel_D_h: float,
    axial_UA: float,
    coolant_as_unknown: bool = False,
    T_inlet: float = T_COOLANT_INLET,
    cp_avg: float = 5500.0,
    gap_conductance: float | None = None,
) -> list[str]:
    """Add one axially-discretized fuel pin.

    If ``coolant_as_unknown`` is True, build a proper energy-advection
    chain: inlet Dirichlet → interior coolant slice 0 → ... → slice
    n_axial-1 → outlet Dirichlet sink. Each interior coolant slice is
    solved by netflow, receiving convective Q from its clad-outer and
    transporting it downstream via ``CoolantAdvection``.

    If ``coolant_as_unknown`` is False (the original v1 behaviour), each
    slice's coolant is a Dirichlet node fixed to a precomputed enthalpy
    rise using the *average* q_lin (which is wrong for non-identical
    pins — they all see the assembly-average coolant T).
    """
    clad_outer_ids: list[str] = []
    A_ht_per_slice = math.pi * ROD_OD * slice_L

    # If coolant is solved, set up the inlet Dirichlet and outlet sink
    # once per pin.
    if coolant_as_unknown:
        inlet_id = f"{pin_id}_cool_inlet"
        outlet_id = f"{pin_id}_cool_outlet"
        network.add_node(Node(id=inlet_id, fixed=T_inlet))
        # The outlet sink only absorbs outflow; its Dirichlet value is
        # never used by any flux because the advection edge into it
        # carries mdot·cp·T_upstream (depends on upstream only).
        network.add_node(Node(id=outlet_id, fixed=T_inlet))

    prev_clad_outer: str | None = None
    prev_coolant_id: str | None = inlet_id if coolant_as_unknown else None

    for k in range(n_axial):
        prefix = f"{pin_id}_z{k}_"

        rod = FuelRod(
            r_pellet=R_PELLET,
            gap_thickness=GAP_THICKNESS,
            r_clad_outer=R_CLAD_OUTER,
            L=slice_L,
            fuel_material=UO2(),
            clad_material=Zircaloy4(),
            gap_material=Helium_gap,
            gap_emissivity=0.85,
            q_lin=q_lin_per_slice[k],
            gap_conductance=gap_conductance,
        )
        ports = rod.build(network, prefix=prefix)

        coolant_id = f"{pin_id}_cool_z{k}"

        if coolant_as_unknown:
            # Capacity = mass of water in the subchannel slice × cp.
            # Mass ≈ ρ · A_xs · slice_L, with ρ ~700 kg/m³ at PWR conditions.
            C_cool = 700.0 * subchannel_A_xs * slice_L * cp_avg
            network.add_node(Node(
                id=coolant_id, state0=coolant_Ts[k], capacity=C_cool,
            ))
            # Advection edge: prev_coolant → this_coolant
            network.add_edge(CoolantAdvection(
                prev_coolant_id, coolant_id,
                mdot=MDOT_CHANNEL, cp=cp_avg,
            ))
            prev_coolant_id = coolant_id
        else:
            # Original v1 behaviour: Dirichlet from precompute
            network.add_node(Node(id=coolant_id, fixed=coolant_Ts[k]))

        # Forced convection clad_outer → coolant (same in both cases)
        network.add_edge(ForcedConvection(
            ports.clad_outer, coolant_id,
            fluid=coolant,
            mdot=MDOT_CHANNEL,
            D_h=subchannel_D_h,
            A_ht=A_ht_per_slice,
            A_xs=subchannel_A_xs,
            correlation="dittus-boelter",
            wall_side="a",
        ))

        if prev_clad_outer is not None and axial_UA > 0:
            network.add_edge(UAEdge(prev_clad_outer, ports.clad_outer, UA=axial_UA))
        prev_clad_outer = ports.clad_outer
        clad_outer_ids.append(ports.clad_outer)

    # Closing advection edge from last interior coolant to outlet sink
    if coolant_as_unknown and prev_coolant_id is not None:
        network.add_edge(CoolantAdvection(
            prev_coolant_id, outlet_id,
            mdot=MDOT_CHANNEL, cp=cp_avg,
        ))

    return clad_outer_ids


from typing import Callable, Union

QLinSpec = Union[float, Callable[[int, int], float]]  # float OR (ix,iy) → q_lin


def cosine_radial_power(
    n_x: int, n_y: int, *,
    q_lin_avg: float = Q_LIN_NOMINAL,
    peak_factor: float = 1.4,
) -> Callable[[int, int], float]:
    """Realistic PWR radial power tilt: cosine drop from center to edge.

    Peak at the central pin equals ``peak_factor * q_lin_avg``; pins on
    the diagonal corners drop toward (2 − peak_factor) · q_lin_avg
    so the assembly average is approximately preserved.
    """
    cx = (n_x - 1) / 2
    cy = (n_y - 1) / 2
    r_max = math.hypot(cx, cy) or 1.0

    def q_at(ix: int, iy: int) -> float:
        r = math.hypot(ix - cx, iy - cy) / r_max
        shape = math.cos(min(r, 1.0) * math.pi / 2)  # 1 at center, 0 at corner
        # Scale so that center = peak_factor, edge = (2 − peak_factor)
        return q_lin_avg * ((peak_factor - 1.0) * shape + 1.0)

    return q_at


def _resolve_q_lin(q_lin: QLinSpec, ix: int, iy: int) -> float:
    return float(q_lin(ix, iy)) if callable(q_lin) else float(q_lin)


def _avg_q_lin(q_lin: QLinSpec, n_x: int, n_y: int) -> float:
    if not callable(q_lin):
        return float(q_lin)
    total = 0.0
    for ix in range(n_x):
        for iy in range(n_y):
            total += float(q_lin(ix, iy))
    return total / (n_x * n_y)


def build_pin_assembly(
    *,
    n_x: int,
    n_y: int,
    n_axial: int,
    L_total: float = 1.5,
    q_lin: QLinSpec = Q_LIN_NOMINAL,
    coolant_fluid: CoolPropFluid | None = None,
    coolant_as_unknown: bool = False,
    axial_shape: Callable[[float], float] | None = None,
    cross_pin_mixing_fraction: float = 0.0,
    gap_conductance: float | None = None,
) -> tuple[Network, dict]:
    """Tile ``n_x × n_y`` axially-discretized pins.

    Parameters
    ----------
    q_lin :
        Either a single float (all pins identical) or a callable
        ``(ix, iy) -> q_lin`` for non-identical pins. The coolant
        axial temperatures are computed from the *average* q_lin so
        every pin sees the same channel-bulk profile (per-pin
        subchannel coolant evolution is a v2 concern).
    coolant_fluid :
        Optional pre-built ``CoolPropFluid``. Reusing one across
        builds also reuses its property cache.
    """
    slice_L = L_total / n_axial
    q_avg = _avg_q_lin(q_lin, n_x, n_y)
    coolant_Ts = coolant_axial_temps(
        n_axial, slice_L, q_avg, axial_shape=axial_shape,
    )
    coolant = coolant_fluid or CoolPropFluid("Water", default_P=P_SYSTEM)

    # Precompute per-slice axial multipliers once (used per pin below).
    z_norms = [(k + 0.5) / n_axial for k in range(n_axial)]
    if axial_shape is not None:
        axial_mult = [axial_shape(z) for z in z_norms]
    else:
        axial_mult = [1.0] * n_axial

    A_xs_sub = PITCH ** 2 - math.pi * ROD_OD ** 2 / 4
    D_h_sub = 4 * A_xs_sub / (math.pi * ROD_OD)

    # Tiny axial UA: rod-structural conduction between adjacent slice clad-outers.
    axial_UA = 14.0 * (2 * math.pi * R_CLAD_OUTER * (R_CLAD_OUTER - 4.185e-3)) / slice_L

    net = Network()
    q_min = float("inf"); q_max = -float("inf")
    for ix in range(n_x):
        for iy in range(n_y):
            q_here = _resolve_q_lin(q_lin, ix, iy)
            q_min = min(q_min, q_here)
            q_max = max(q_max, q_here)
            q_lin_per_slice = [q_here * m for m in axial_mult]
            _add_axial_pin(
                net,
                pin_id=f"p{ix}_{iy}",
                n_axial=n_axial,
                slice_L=slice_L,
                q_lin_per_slice=q_lin_per_slice,
                coolant_Ts=coolant_Ts,
                coolant=coolant,
                subchannel_A_xs=A_xs_sub,
                subchannel_D_h=D_h_sub,
                axial_UA=axial_UA,
                coolant_as_unknown=coolant_as_unknown,
                gap_conductance=gap_conductance,
            )

    # Cross-pin coolant mixing — turbulent diffusive lateral exchange.
    # Adds CoolantMixing edges between adjacent pins' coolant nodes at
    # each axial slice. Only effective when coolant is a solved unknown
    # (Dirichlet coolant has no lateral DOF to couple).
    if cross_pin_mixing_fraction > 0:
        if not coolant_as_unknown:
            raise ValueError(
                "cross_pin_mixing_fraction > 0 requires "
                "coolant_as_unknown=True"
            )
        mdot_mix = cross_pin_mixing_fraction * MDOT_CHANNEL
        cp_mix = 5500.0
        for ix in range(n_x):
            for iy in range(n_y):
                for k in range(n_axial):
                    here = f"p{ix}_{iy}_cool_z{k}"
                    if ix + 1 < n_x:
                        right = f"p{ix+1}_{iy}_cool_z{k}"
                        net.add_edge(CoolantMixing(
                            here, right, mdot_mix=mdot_mix, cp=cp_mix,
                        ))
                    if iy + 1 < n_y:
                        up = f"p{ix}_{iy+1}_cool_z{k}"
                        net.add_edge(CoolantMixing(
                            here, up, mdot_mix=mdot_mix, cp=cp_mix,
                        ))

    n_pins = n_x * n_y
    meta = {
        "n_pins": n_pins,
        "n_axial": n_axial,
        "slice_L": slice_L,
        "coolant_T_inlet": coolant_Ts[0],
        "coolant_T_outlet": coolant_Ts[-1],
        "label": f"{n_x}×{n_y} × {n_axial} axial",
        "q_lin_avg": q_avg,
        "q_lin_min": q_min,
        "q_lin_max": q_max,
        "q_lin_peak_factor": q_max / q_avg if q_avg > 0 else 1.0,
        "coolant_as_unknown": coolant_as_unknown,
        "axial_shape": (
            f"cosine peak/avg={axial_shape.peak_factor}"
            if axial_shape is not None and hasattr(axial_shape, "peak_factor")
            else ("custom" if axial_shape is not None else "uniform")
        ),
        "cross_pin_mixing_fraction": cross_pin_mixing_fraction,
    }
    return net, meta


# ---------------------------------------------------------------------------
# Scaling sweep
# ---------------------------------------------------------------------------

@dataclass
class ScaleRecord:
    label: str
    n_pins: int
    n_axial: int
    n_nodes: int
    n_interior: int
    n_edges: int
    setup_s: float
    solve_s: float
    n_iter: int
    converged: bool
    residual: float
    T_centerline_peak: float
    q_lin_peak_factor: float = 1.0


def _print_header() -> None:
    print(f"{'config':>16s} | {'nodes':>7s} | {'edges':>8s} | "
          f"{'setup':>8s} | {'solve':>8s} | {'iter':>5s} | {'T_max (°C)':>10s}")
    print("-" * 80)


def run_scale_sweep(
    ladder: list[tuple[int, int]],
    *,
    n_axial: int = 30,
    print_header: bool = True,
    q_lin: QLinSpec = Q_LIN_NOMINAL,
    coolant_fluid: CoolPropFluid | None = None,
) -> list[ScaleRecord]:
    """Run a list of (n_x, n_y) sizes and collect records.

    ``coolant_fluid`` may be passed in to share a CoolPropFluid
    (and its property cache) across all entries in the ladder.
    ``q_lin`` may be a float or a callable ``(ix, iy) -> q_lin`` for
    non-identical pins.
    """
    if print_header:
        _print_header()

    records: list[ScaleRecord] = []
    for (n_x, n_y) in ladder:
        t0 = time.perf_counter()
        net, meta = build_pin_assembly(
            n_x=n_x, n_y=n_y, n_axial=n_axial,
            q_lin=q_lin, coolant_fluid=coolant_fluid,
        )
        setup_s = time.perf_counter() - t0

        n_nodes = len(net.nodes)
        n_edges = len(net.edges)
        n_interior = sum(1 for n in net.nodes.values() if not n.is_dirichlet)

        t1 = time.perf_counter()
        try:
            res = net.solve_steady(method="newton", tol=1e-5, max_iter=80)
            solve_s = time.perf_counter() - t1
            T_peak = max(
                v for k, v in res.states.items() if k.endswith("_centerline")
            )
            label = meta["label"]
            rec = ScaleRecord(
                label=label,
                n_pins=meta["n_pins"], n_axial=meta["n_axial"],
                n_nodes=n_nodes, n_interior=n_interior, n_edges=n_edges,
                setup_s=setup_s, solve_s=solve_s,
                n_iter=res.n_iter, converged=res.converged,
                residual=float(res.residual_history[-1]),
                T_centerline_peak=T_peak,
                q_lin_peak_factor=meta["q_lin_peak_factor"],
            )
            marker = "" if res.converged else " !!"
            print(f"{label:>16s} | {n_nodes:>7d} | {n_edges:>8d} | "
                  f"{setup_s:>7.2f}s | {solve_s:>7.2f}s | {res.n_iter:>5d} | "
                  f"{T_peak-273.15:>10.1f}{marker}")
        except Exception as exc:  # noqa: BLE001
            solve_s = time.perf_counter() - t1
            print(f"{meta['label']:>16s} | FAILED after {solve_s:.1f}s: {exc}")
            rec = ScaleRecord(
                label=meta["label"],
                n_pins=meta["n_pins"], n_axial=meta["n_axial"],
                n_nodes=n_nodes, n_interior=n_interior, n_edges=n_edges,
                setup_s=setup_s, solve_s=solve_s,
                n_iter=-1, converged=False, residual=float("nan"),
                T_centerline_peak=float("nan"),
            )
        records.append(rec)
    return records


def plot_scaling(records: list[ScaleRecord], out_path: pathlib.Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    converged = [r for r in records if r.converged]
    if not converged:
        print("no converged runs to plot")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    n = [r.n_nodes for r in converged]
    t_solve = [r.solve_s for r in converged]
    t_setup = [r.setup_s for r in converged]
    n_iter = [r.n_iter for r in converged]

    ax1.loglog(n, t_solve, marker="o", linewidth=2, label="solve")
    ax1.loglog(n, t_setup, marker="s", linewidth=1.5, label="setup")
    # Reference slopes
    if len(n) >= 2:
        n_arr = sorted(n)
        # O(N): use first measurement to anchor
        t0_solve = t_solve[n.index(min(n))]
        t_linear = [t0_solve * (x / min(n)) for x in n_arr]
        t_quad = [t0_solve * (x / min(n))**2 for x in n_arr]
        ax1.plot(n_arr, t_linear, linestyle=":", color="gray", alpha=0.5,
                 label="O(N)")
        ax1.plot(n_arr, t_quad, linestyle="--", color="gray", alpha=0.5,
                 label="O(N²)")
    ax1.set_xlabel("nodes")
    ax1.set_ylabel("time (s)")
    ax1.set_title("Time to setup and solve")
    ax1.grid(True, which="both", alpha=0.3)
    ax1.legend(fontsize=9)

    ax2.semilogx(n, n_iter, marker="o", linewidth=2, color="#cc3333")
    ax2.set_xlabel("nodes")
    ax2.set_ylabel("Newton iterations")
    ax2.set_title("Newton iterations vs problem size")
    ax2.grid(True, which="both", alpha=0.3)
    # Annotate each point with the label
    for r, x, y in zip(converged, n, n_iter):
        ax2.annotate(r.label, xy=(x, y), xytext=(4, 4),
                     textcoords="offset points", fontsize=7)

    fig.tight_layout()
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    print(f"  wrote {out_path}")


# ---------------------------------------------------------------------------
# Main / CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--axial", type=int, default=30)
    parser.add_argument("--max-pins", type=int, default=17)
    parser.add_argument("--plot", action="store_true")
    parser.add_argument("--time-budget", type=float, default=180.0)
    parser.add_argument(
        "--non-identical", action="store_true",
        help="Apply a realistic cosine radial power tilt "
             "(peak/avg = 1.4) instead of identical pins.",
    )
    parser.add_argument(
        "--cache-resolution", type=float, default=0.05,
        help="CoolProp cache T resolution in K (0 disables cache).",
    )
    parser.add_argument(
        "--out", type=pathlib.Path, default=pathlib.Path("results"),
        help="output directory for plots",
    )
    args = parser.parse_args()

    ladder_widths = [1, 2, 3, 5, 9]
    for w in [17, 25, 34, 50, 75, 100, 150, 200]:
        if w <= args.max_pins:
            ladder_widths.append(w)
    ladder = [(w, w) for w in ladder_widths]

    # Shared fluid so the cache persists across the ladder.
    coolant = CoolPropFluid(
        "Water", default_P=P_SYSTEM,
        cache_T_resolution=args.cache_resolution,
    )

    print(f"Axial slices per pin: {args.axial}")
    print(f"Largest pin grid: {args.max_pins}×{args.max_pins}")
    print(f"Cache resolution: {args.cache_resolution} K"
          + (" (disabled)" if args.cache_resolution == 0 else ""))
    print(f"Pin power: {'cosine radial tilt (peak/avg=1.4)' if args.non_identical else 'identical pins'}")
    print()

    # Warm-up call (CoolProp + numpy/scipy JIT) so the first sweep
    # entry doesn't double-count cold-start cost.
    warm_net, _ = build_pin_assembly(n_x=1, n_y=1, n_axial=args.axial,
                                     coolant_fluid=coolant)
    warm_net.solve_steady()
    print("[warm-up done; CoolProp + scipy initialised]\n")

    _print_header()
    records: list[ScaleRecord] = []
    for (n_x, n_y) in ladder:
        if args.non_identical:
            q_spec: QLinSpec = cosine_radial_power(n_x, n_y)
        else:
            q_spec = Q_LIN_NOMINAL
        sub = run_scale_sweep(
            [(n_x, n_y)], n_axial=args.axial, print_header=False,
            q_lin=q_spec, coolant_fluid=coolant,
        )
        records.extend(sub)
        if sub and sub[-1].solve_s > args.time_budget:
            print(f"\n[Accountant] solve exceeded {args.time_budget:.0f}s "
                  f"budget at {sub[-1].label} — stopping sweep.")
            break

    print(f"\ncache stats: {coolant.cache_stats()}")

    if args.plot and records:
        args.out.mkdir(parents=True, exist_ok=True)
        suffix = "_nonidentical" if args.non_identical else ""
        plot_scaling(records, args.out / f"fuel_array_scaling{suffix}.png")

    print()
    print("=" * 80)
    print("Scale-test summary")
    print("=" * 80)
    for r in records:
        status = "✓" if r.converged else "✗"
        tag = f" (peak/avg={r.q_lin_peak_factor:.2f})" if r.q_lin_peak_factor != 1.0 else ""
        print(f"  {status}  {r.label:>16s}  "
              f"nodes={r.n_nodes:>7d}  edges={r.n_edges:>8d}  "
              f"solve={r.solve_s:>7.2f}s  iter={r.n_iter}{tag}")


if __name__ == "__main__":
    main()
