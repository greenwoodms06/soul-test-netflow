"""Render the cross-paradigm scaling figure for the bundle README.

One panel, log-log: wall time vs problem size, three paradigms on the
same axes. Each curve is labeled with what its time measures
(apples-to-oranges by definition — see caption / README).

Data sources:
  - netflow: published linear sparse-LU scaling (~190 s @ 380k linear
    nodes) + single-pin Newton time (9 ms). Anchor docs in
    python/CONTEXT.md and python/docs/VALIDATION.md.
  - julia-mtk: mtkcompile per-component cost ~71 s @ 2k unknowns,
    exponent ~N^1.6 (MTK-F4/F9), extrapolated 25-40 min @ 40k unknowns
    (17x17x30). Sim-time-only is dramatically lower (0.064s @ 10k) but
    the WALL is the compile.
  - modelica: full physics_breadth_ladder.json + stress_assembly_*.json
    in modelica/results/.
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


def _load(rel):
    path = os.path.join(REPO_ROOT, rel)
    if not os.path.isfile(path):
        return []
    with open(path) as f:
        return json.load(f)


def main() -> int:
    # ----- netflow: linear sparse-Newton (Newton solve time only) ------------
    # Anchors: single pin 9 ms; full PWR core 380k nodes ~ 190 s.
    # Slope is ~linear in N (sparse LU). Plot two anchor points + an O(N) line
    # through them.
    nf_nodes = np.array([1, 380_000])
    nf_wall = np.array([0.009, 190.0])

    # ----- julia-mtk: mtkcompile codegen cost (the wall) ---------------------
    # Anchors (MTK-F4/F9 from COMPARISON.md): ~71 s mtkcompile alone at 2k
    # unknowns; exponent ~N^1.6 across the ladder; extrapolated 25-40 min @
    # ~40k unknowns (17x17x30). We plot the measured anchor + the extrapolation
    # as a dashed continuation.
    mtk_nodes_measured = np.array([2000, 10_000])     # last measured before wall
    mtk_wall_measured = np.array([71.0, 71.0 * (10_000 / 2000) ** 1.6])
    mtk_nodes_extrap = np.array([10_000, 40_000])
    mtk_wall_extrap = np.array([
        71.0 * (10_000 / 2000) ** 1.6,
        71.0 * (40_000 / 2000) ** 1.6,
    ])

    # ----- modelica: full ladder (end-to-end translate+compile+sim) ---------
    breadth = _load("modelica/results/physics_breadth_ladder.json")
    s25 = _load("modelica/results/stress_assembly_25x25.json")

    mod_pts = []  # list of (nodes, wall) for AssemblyVeraP6 vanilla
    for r in breadth:
        if r.get("variant") == "AssemblyVeraP6" and r.get("ok"):
            kw = r["kwargs"]
            nodes = kw["n_pin"] * kw["n_axial"]
            mod_pts.append((nodes, r["wall_s"]))
    for r in s25:
        if r.get("ok"):
            nodes = r["n_pin"] * r["n_axial"]
            mod_pts.append((nodes, r["wall_s"]))
    # The OOM point (n_pin=484, n_axial=30, ok=False) — record nodes for the
    # wall marker.
    mod_oom = None
    for r in s25:
        if not r.get("ok"):
            mod_oom = r["n_pin"] * r["n_axial"]
            break
    mod_pts.sort()
    mod_nodes = np.array([p[0] for p in mod_pts])
    mod_wall = np.array([p[1] for p in mod_pts])

    # ---- prior 17x17 ladder (Assembly17x17 baseline from COMPARISON.md §3b)
    prior_17x17 = [
        (160, 8.1),
        (640, 22.7),
        (1280, 41.3),
        (2890, 105.9),
        (5780, 227.2),
        (8670, 397.1),
    ]
    prior_n = np.array([p[0] for p in prior_17x17])
    prior_w = np.array([p[1] for p in prior_17x17])

    # ============================== PLOT ===================================
    fig, ax = plt.subplots(figsize=(10, 7))

    # netflow line (linear sparse, Newton solve only)
    ax.plot(nf_nodes, nf_wall, "o-", color="#1f77b4", lw=2, markersize=9,
            label="Python netflow (sparse-LU Newton solve only)")
    ax.annotate("9 ms (1 pin)", xy=(nf_nodes[0], nf_wall[0]),
                xytext=(2, -18), textcoords="offset points",
                fontsize=8, color="#1f77b4")
    ax.annotate("~190 s\n@ 380k nodes\n(full PWR core)",
                xy=(nf_nodes[1], nf_wall[1]),
                xytext=(8, -8), textcoords="offset points",
                fontsize=8, color="#1f77b4")

    # MTK measured
    ax.plot(mtk_nodes_measured, mtk_wall_measured, "s-", color="#ff7f0e",
            lw=2, markersize=9,
            label="Julia / MTK mtkcompile (codegen wall; ~N^1.6)")
    # MTK extrapolated dashed
    ax.plot(mtk_nodes_extrap, mtk_wall_extrap, "s--", color="#ff7f0e",
            lw=2, markersize=9, alpha=0.55)
    ax.annotate("~71 s\n@ 2k unknowns\n(MTK-F4)",
                xy=(mtk_nodes_measured[0], mtk_wall_measured[0]),
                xytext=(-65, 4), textcoords="offset points",
                fontsize=8, color="#ff7f0e")
    ax.annotate("extrapolated\n25-40 min\n@ 17×17×30,\nnever run\n(MTK-F9)",
                xy=(mtk_nodes_extrap[1], mtk_wall_extrap[1]),
                xytext=(-115, -8), textcoords="offset points",
                fontsize=8, color="#ff7f0e",
                arrowprops=dict(arrowstyle="->", color="#ff7f0e", lw=0.8))

    # Modelica: prior 17×17 + new 25×25 ladder, end-to-end
    ax.plot(prior_n, prior_w, "^-", color="#d62728", lw=2, markersize=8,
            label="Modelica / Dymola end-to-end (translate + cc1 compile + sim)")
    # 25×25 extension (red squares, same colour family)
    ext_n = np.array([p[0] for p in mod_pts if p[0] > 8670])
    ext_w = np.array([p[1] for p in mod_pts if p[0] > 8670])
    if len(ext_n) > 0:
        ax.plot(np.concatenate([[8670], ext_n]),
                np.concatenate([[397.1], ext_w]),
                "D-", color="#d62728", lw=2, markersize=8, alpha=0.65)
    ax.annotate("397 s\n@ 17×17×30",
                xy=(8670, 397.1), xytext=(-65, -22), textcoords="offset points",
                fontsize=8, color="#d62728")
    if mod_oom:
        ax.scatter([mod_oom], [600], marker="X", s=260, color="#d62728",
                   edgecolor="black", linewidth=1.4, zorder=10)
        ax.annotate("cc1 OOM\n@ 22×22×30,\n19.9 GB RAM\n(MO-F20)",
                    xy=(mod_oom, 600), xytext=(12, -8),
                    textcoords="offset points",
                    fontsize=8, color="#d62728",
                    arrowprops=dict(arrowstyle="->", color="#d62728", lw=0.8))

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Problem size (pin nodes or unknowns)", fontsize=10)
    ax.set_ylabel("Wall time (s)", fontsize=10)
    ax.set_title("Three solver paradigms on one PWR pin / coolant chain\n"
                 "Same physics, three paradigms, one machine — "
                 "where each paradigm's wall lives",
                 fontsize=11)
    ax.legend(loc="upper left", fontsize=9, framealpha=0.95)
    ax.grid(which="both", linestyle=":", alpha=0.4)

    caption = (
        "Three paradigms measure different things: netflow is the pure sparse-LU Newton solve (no compile); "
        "Julia/MTK's wall is the per-component `mtkcompile` codegen (the simulator is much faster once it's built); "
        "Modelica/Dymola is the full translate → C codegen → gcc → dymosim end-to-end time. "
        "The chart isn't a fair time race — it's a 'where does each paradigm hit a wall' map. "
        "All three paradigms could in principle handle the 17×17×30 anchor; only two of them actually did."
    )
    fig.text(0.06, 0.02, caption, fontsize=8, wrap=True, style="italic",
             color="#444")
    fig.subplots_adjust(bottom=0.18)

    out = os.path.join(REPO_ROOT, "three_paradigm_walls.png")
    fig.savefig(out, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
