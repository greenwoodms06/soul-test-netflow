"""Generate the full visualization suite for a fuel-pin assembly solve.

Outputs (default to ``results/`` next to the cwd):

* ``assembly_heatmap.png``         — top-down peak-T heatmap + q_lin map
* ``assembly_hottest_pin.png``     — axial T profile of the hottest pin
* ``assembly_3d.html``             — interactive plotly viewer

Run:

    python -m netflow.plugins.thermal.examples.assembly_visualizer
    python -m netflow.plugins.thermal.examples.assembly_visualizer \\
        --pins 17 --axial 30 --non-identical
"""

from __future__ import annotations

import argparse
import pathlib
import time

from netflow.bench.fuel_array import (
    Q_LIN_NOMINAL,
    build_pin_assembly,
    cosine_axial_shape,
    cosine_radial_power,
)
from netflow.plugins.thermal import CoolPropFluid
from netflow.viz_interactive import (
    extract_assembly_data,
    make_interactive_assembly_view,
    plot_assembly_heatmap,
    plot_hottest_pin_axial,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pins", type=int, default=17,
                        help="grid is pins×pins (default 17 = PWR assembly)")
    parser.add_argument("--axial", type=int, default=30,
                        help="axial slices per pin (default 30)")
    parser.add_argument("--non-identical", action="store_true",
                        help="apply cosine radial power tilt peak/avg=1.4")
    parser.add_argument("--peak-factor", type=float, default=1.4,
                        help="non-identical peak/avg (default 1.4)")
    parser.add_argument("--coolant-as-unknown", action="store_true",
                        help="treat coolant as solved variable with energy "
                             "advection (instead of Dirichlet from precompute)")
    parser.add_argument("--axial-shape", choices=["uniform", "cosine"],
                        default="uniform",
                        help="axial power shape (default uniform)")
    parser.add_argument("--axial-peak-factor", type=float, default=1.5,
                        help="peak/avg for cosine axial shape (default 1.5)")
    parser.add_argument("--cross-pin-mixing", type=float, default=0.0,
                        help="lateral mixing fraction (e.g. 0.05). "
                             "Requires --coolant-as-unknown.")
    parser.add_argument("--out", type=pathlib.Path,
                        default=pathlib.Path("results"))
    args = parser.parse_args()

    print(f"Building {args.pins}×{args.pins} × {args.axial} axial "
          f"({'non-identical' if args.non_identical else 'identical'} pins)…")
    fluid = CoolPropFluid("Water", default_P=15.5e6, cache_T_resolution=0.05)

    if args.non_identical:
        q_fn = cosine_radial_power(
            args.pins, args.pins, peak_factor=args.peak_factor,
        )
    else:
        q_fn = Q_LIN_NOMINAL

    axial_shape = (
        cosine_axial_shape(args.axial_peak_factor)
        if args.axial_shape == "cosine"
        else None
    )

    t0 = time.perf_counter()
    net, meta = build_pin_assembly(
        n_x=args.pins, n_y=args.pins, n_axial=args.axial,
        q_lin=q_fn, coolant_fluid=fluid,
        coolant_as_unknown=args.coolant_as_unknown,
        axial_shape=axial_shape,
        cross_pin_mixing_fraction=args.cross_pin_mixing,
    )
    setup_s = time.perf_counter() - t0

    print(f"  setup: {setup_s:.2f}s  ({len(net.nodes)} nodes, {len(net.edges)} edges)")
    print(f"  solving…")
    t1 = time.perf_counter()
    res = net.solve_steady(method="newton", tol=1e-5, max_iter=80)
    solve_s = time.perf_counter() - t1
    print(f"  solved in {solve_s:.2f}s — converged={res.converged}, iter={res.n_iter}")
    print()

    q_lin_for_extract = q_fn if args.non_identical else (lambda ix, iy: Q_LIN_NOMINAL)
    data = extract_assembly_data(
        net, res,
        n_x=args.pins, n_y=args.pins, n_axial=args.axial,
        slice_L=meta["slice_L"], q_lin_fn=q_lin_for_extract,
    )

    print(f"  peak centerline T: {data.peak_T_per_pin.max() - 273.15:.1f} °C")
    print(f"  min centerline T : {data.peak_T_per_pin.min() - 273.15:.1f} °C")
    print()

    args.out.mkdir(parents=True, exist_ok=True)
    suffix = "_nonidentical" if args.non_identical else "_identical"
    if args.coolant_as_unknown:
        suffix += "_coolsolved"
    if args.axial_shape == "cosine":
        suffix += f"_axcos{args.axial_peak_factor}"
    if args.cross_pin_mixing > 0:
        suffix += f"_mix{args.cross_pin_mixing}"

    print("Writing visualizations:")
    coolant_mode = "coolant solved" if args.coolant_as_unknown else "coolant Dirichlet"
    axial_mode = (
        f"axial cos peak/avg={args.axial_peak_factor}"
        if args.axial_shape == "cosine"
        else "axial uniform"
    )
    plot_assembly_heatmap(
        data, args.out / f"assembly_heatmap{suffix}.png",
        title=(
            f"PWR-like fuel-pin assembly  ·  {args.pins}×{args.pins} pins  ·  "
            f"{args.axial} axial slices  ·  "
            f"{'radial tilt peak/avg='+str(args.peak_factor) if args.non_identical else 'identical pins'}"
            f"  ·  {coolant_mode}  ·  {axial_mode}"
        ),
    )
    plot_hottest_pin_axial(data, args.out / f"assembly_hottest_pin{suffix}.png")
    make_interactive_assembly_view(
        data, args.out / f"assembly_3d{suffix}.html",
        title=(
            f"PWR fuel-pin assembly — {args.pins}×{args.pins} pins · "
            f"{args.axial} axial · "
            f"{'tilted' if args.non_identical else 'uniform'}"
        ),
    )

    print()
    print(f"Open the interactive viewer with:")
    print(f"  xdg-open {args.out / f'assembly_3d{suffix}.html'}     # WSL/Linux")
    print(f"  or just double-click it in the file manager")


if __name__ == "__main__":
    main()
