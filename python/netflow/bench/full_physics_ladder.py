"""Push the scale ladder under the full physics stack until we hit a wall.

Full physics = non-identical radial tilt + cosine axial shape + solved
coolant + cross-pin mixing. Each entry reports setup, solve, Newton iter,
peak T, RSS memory. The Accountant halts when solve time exceeds a
budget or memory passes a threshold.

Run unbuffered:
    python -u -m netflow.bench.full_physics_ladder
"""

from __future__ import annotations

import argparse
import gc
import os
import sys
import time

from netflow.bench.fuel_array import (
    build_pin_assembly,
    cosine_axial_shape,
    cosine_radial_power,
)
from netflow.plugins.thermal import CoolPropFluid


def _rss_mb() -> float:
    try:
        with open(f"/proc/{os.getpid()}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0
    except OSError:
        pass
    return float("nan")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--axial", type=int, default=30)
    parser.add_argument("--mix", type=float, default=0.05)
    parser.add_argument("--peak-axial", type=float, default=1.5)
    parser.add_argument("--peak-radial", type=float, default=1.4)
    parser.add_argument(
        "--sizes", type=int, nargs="+",
        default=[5, 9, 17, 25, 34, 50, 75, 100, 125, 150],
    )
    parser.add_argument("--time-budget", type=float, default=120.0,
                        help="stop if a single solve exceeds this many seconds")
    parser.add_argument("--memory-budget-gb", type=float, default=18.0,
                        help="stop if RSS exceeds this many GB after a solve")
    args = parser.parse_args()

    fluid = CoolPropFluid("Water", default_P=15.5e6)
    ax = cosine_axial_shape(args.peak_axial)

    print(f"Full-physics ladder: axial={args.axial}, mix={args.mix}, "
          f"radial peak/avg={args.peak_radial}, axial peak/avg={args.peak_axial}",
          flush=True)
    print(f"Budgets: solve ≤ {args.time_budget:.0f}s, "
          f"RSS ≤ {args.memory_budget_gb:.1f} GB\n", flush=True)

    # Warm-up
    q_warm = cosine_radial_power(2, 2, peak_factor=args.peak_radial)
    net, _ = build_pin_assembly(
        n_x=2, n_y=2, n_axial=args.axial, q_lin=q_warm, axial_shape=ax,
        coolant_fluid=fluid, coolant_as_unknown=True,
        cross_pin_mixing_fraction=args.mix,
    )
    net.solve_steady()
    print(f"[warm-up done, RSS = {_rss_mb():.0f} MB]\n", flush=True)

    print(f"{'config':>16s} | {'nodes':>7s} | {'edges':>9s} | "
          f"{'setup':>9s} | {'solve':>9s} | {'iter':>4s} | {'RSS':>8s} | "
          f"{'peak T':>9s}", flush=True)
    print("-" * 95, flush=True)

    for N in args.sizes:
        gc.collect()
        t0 = time.perf_counter()
        q_fn = cosine_radial_power(N, N, peak_factor=args.peak_radial)
        try:
            net, _ = build_pin_assembly(
                n_x=N, n_y=N, n_axial=args.axial, q_lin=q_fn, axial_shape=ax,
                coolant_fluid=fluid, coolant_as_unknown=True,
                cross_pin_mixing_fraction=args.mix,
            )
        except MemoryError as exc:
            print(f"{N}×{N}×{args.axial} mix={args.mix} | "
                  f"BUILD FAILED — MemoryError: {exc}", flush=True)
            break
        setup_s = time.perf_counter() - t0

        try:
            t1 = time.perf_counter()
            res = net.solve_steady(method="newton", tol=1e-5, max_iter=80)
            solve_s = time.perf_counter() - t1
        except MemoryError as exc:
            solve_s = time.perf_counter() - t1
            print(f"{N}×{N}×{args.axial} mix={args.mix} | "
                  f"nodes={len(net.nodes)} edges={len(net.edges)} "
                  f"SOLVE FAILED after {solve_s:.1f}s — MemoryError: {exc}",
                  flush=True)
            break

        rss_mb = _rss_mb()
        if res.converged:
            cl_peak = max(v for k, v in res.states.items() if "centerline" in k)
            cl_peak_C = cl_peak - 273.15
        else:
            cl_peak_C = float("nan")

        marker = "" if res.converged else " ✗ NOT CONVERGED"
        print(f"{N}×{N}×{args.axial} mix={args.mix} | "
              f"{len(net.nodes):>7d} | {len(net.edges):>9d} | "
              f"{setup_s:>7.2f} s | {solve_s:>7.2f} s | {res.n_iter:>4d} | "
              f"{rss_mb:>6.0f} MB | {cl_peak_C:>7.1f} °C{marker}",
              flush=True)

        if solve_s > args.time_budget:
            print(f"\n[Accountant] solve exceeded {args.time_budget:.0f}s "
                  f"budget at N={N} — stopping ladder.", flush=True)
            break
        if rss_mb > args.memory_budget_gb * 1024:
            print(f"\n[Accountant] RSS exceeded "
                  f"{args.memory_budget_gb:.1f} GB at N={N} — stopping ladder.",
                  flush=True)
            break

        # Drop references so GC can reclaim before the next size
        del net, res
        gc.collect()

    print("\nLadder done.", flush=True)


if __name__ == "__main__":
    main()
