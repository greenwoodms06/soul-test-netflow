"""Plot the 2026-05-26-unfreeze headline figure for COMPARISON.md update.

Two panels:
  A — Flag-vs-scale: where does each flag actually move the wall?
      Bar groups by scale (chain N=2500, chain N=5000, asm 17x17x30).
      Bars within group = scenarios (default, sparse, sparse+cvode, sparse+esdirk23a).
      Annotation: speedup vs default per bar.

  B — Physics-breadth scaling: wall time vs problem size for each variant.
      Lines = variants (vanilla / cross-pin / neutronics / subchannel).
      X = total pin nodes (n_pin * n_axial), Y = wall time.
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "results")


def _load_json(name: str):
    path = os.path.join(OUT_DIR, name)
    if not os.path.isfile(path):
        return None
    with open(path) as f:
        return json.load(f)


def plot_panel_A(ax, part2_rows):
    """Bar groups by scenario kind, bars within group by label."""
    # Group: ('chain', n=2500), ('chain', n=5000), ('assembly', 17x17x30)
    scenarios = ["default", "sparse", "sparse+cvode", "sparse+esdirk23a"]
    groups = [
        ("Chain N=2500\n(sim wall)", "chain", lambda r: r.get("n") == 2500),
        ("Chain N=5000\n(init-solver wall)", "chain", lambda r: r.get("n") == 5000),
        ("17×17×30 assembly\n(cc1 compile wall)", "assembly", lambda r: r.get("n_pin") == 289 and r.get("n_axial") == 30),
    ]

    n_groups = len(groups)
    n_bars = len(scenarios)
    bar_w = 0.18
    x = np.arange(n_groups)
    colors = ["#888888", "#1f77b4", "#2ca02c", "#9467bd"]

    for i, label in enumerate(scenarios):
        walls = []
        for _gname, kind, sel in groups:
            row = next(
                (r for r in part2_rows
                 if r["kind"] == kind and r["label"] == label and sel(r)),
                None,
            )
            walls.append(row["wall_s"] if (row and row.get("ok")) else np.nan)
        bars = ax.bar(x + (i - 1.5) * bar_w, walls, bar_w, label=label,
                      color=colors[i])
        # Annotate non-nan bars with speedup vs first (default) bar in same group.
        for gi, h in enumerate(walls):
            if not np.isfinite(h):
                continue
            default_row = next(
                (r for r in part2_rows
                 if r["kind"] == groups[gi][1] and r["label"] == "default" and groups[gi][2](r)),
                None,
            )
            default_w = (default_row.get("wall_s") if default_row and default_row.get("ok") else np.nan)
            speedup_txt = ""
            if np.isfinite(default_w) and default_w > 0:
                speedup = default_w / h
                if abs(speedup - 1.0) > 0.05:
                    speedup_txt = f"\n{speedup:.2f}×"
            ax.text(bars[gi].get_x() + bar_w / 2, h + 8,
                    f"{h:.0f}{speedup_txt}",
                    ha="center", va="bottom", fontsize=7)

    # Note for chain N=5000 default — it FAILED (>10 min), not measured here
    for gi, (gname, kind, sel) in enumerate(groups):
        if "N=5000" in gname:
            ax.annotate("default FAILED\n(>10 min, never converged)",
                        xy=(gi - 1.5 * bar_w, 50),
                        xytext=(gi - 1.5 * bar_w, 350),
                        ha="center", fontsize=7,
                        color="#aa0000",
                        arrowprops=dict(arrowstyle="->", color="#aa0000",
                                        lw=0.8))

    ax.set_xticks(x)
    ax.set_xticklabels([g[0] for g in groups])
    ax.set_ylabel("Wall time (s)")
    ax.set_title("Advanced flags vs the wall they're meant to move\n"
                 "(SparseActivate cuts sim walls 2.2×; cc1 wall unmoved)")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(axis="y", linestyle=":", alpha=0.4)


def plot_panel_B(ax, breadth_rows):
    """Wall-time vs problem size for each variant."""
    variants = sorted(set(r["variant"] for r in breadth_rows))
    color_map = {
        "AssemblyVeraP6":           "#1f77b4",
        "AssemblyVeraP6CrossPin":   "#ff7f0e",
        "AssemblyVeraP6Neutronics": "#2ca02c",
        "AssemblyVeraP6Subchannel": "#d62728",
    }
    marker_map = {
        "AssemblyVeraP6":           "o",
        "AssemblyVeraP6CrossPin":   "s",
        "AssemblyVeraP6Neutronics": "^",
        "AssemblyVeraP6Subchannel": "D",
    }
    label_map = {
        "AssemblyVeraP6":           "vanilla (parallel-independent)",
        "AssemblyVeraP6CrossPin":   "+ cross-pin conduction",
        "AssemblyVeraP6Neutronics": "+ per-pin neutronics feedback",
        "AssemblyVeraP6Subchannel": "+ subchannel cross-flow",
    }

    for var in variants:
        rows = [r for r in breadth_rows if r["variant"] == var and r.get("ok")]
        rows.sort(key=lambda r: r["kwargs"].get("n_pin", r["kwargs"].get("n_side", 0) ** 2) * r["kwargs"].get("n_axial", 1))
        if not rows:
            continue
        xs = []
        ys = []
        for r in rows:
            kw = r["kwargs"]
            n_pin = kw.get("n_pin", kw.get("n_side", 0) ** 2)
            n_axial = kw["n_axial"]
            xs.append(n_pin * n_axial)
            ys.append(r["wall_s"])
        ax.plot(xs, ys, marker=marker_map.get(var, "o"),
                color=color_map.get(var, "#444"),
                label=label_map.get(var, var), linewidth=1.6)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Pin nodes (n_pin × n_axial)")
    ax.set_ylabel("Wall time (s)")
    ax.set_title("Physics-breadth scaling at MSL-only Modelica/Dymola")
    ax.legend(fontsize=8, loc="upper left")
    ax.grid(linestyle=":", alpha=0.4)


def main() -> int:
    part2 = _load_json("advanced_flag_sweep_part2.json") or []
    breadth = _load_json("physics_breadth_ladder.json") or []
    if not part2 and not breadth:
        print("[no results yet — run part 2 sweep and physics_breadth_ladder first]")
        return 1

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(14, 5.5))
    if part2:
        plot_panel_A(axA, part2)
    else:
        axA.text(0.5, 0.5, "(no part-2 sweep data)", transform=axA.transAxes,
                 ha="center", va="center")
    if breadth:
        plot_panel_B(axB, breadth)
    else:
        axB.text(0.5, 0.5, "(physics-breadth ladder still running)",
                 transform=axB.transAxes, ha="center", va="center")

    fig.suptitle("2026-05-26 unfreeze — advanced flags + physics breadth at MSL-only Modelica/Dymola",
                 fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    out_path = os.path.join(OUT_DIR, "unfreeze_headline.png")
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
