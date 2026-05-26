"""Plot the 17x17 assembly stress-test ladder once it completes."""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    with open(os.path.join(REPO_ROOT, "results", "stress_assembly_17x17.json")) as f:
        rows = json.load(f)

    pin_nodes = [r["n_pin"] * r["n_axial"] for r in rows if r.get("ok")]
    walls = [r["wall_s"] for r in rows if r.get("ok")]
    labels = [f"{r['n_pin']}×{r['n_axial']}" for r in rows if r.get("ok")]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.loglog(pin_nodes, walls, "o-", color="tab:blue", markersize=8)
    for x, y, lbl in zip(pin_nodes, walls, labels):
        ax.annotate(lbl, (x, y), textcoords="offset points", xytext=(8, -2), fontsize=9)

    # Julia anchor
    ax.fill_betweenx([25 * 60, 40 * 60], 1.5e4, 2e4, color="tab:red", alpha=0.2,
                     label="Julia extrapolated mtkcompile @ 17×17×30 (25–40 min)")
    ax.axhline(60, ls=":", color="gray", alpha=0.5, label="1 min")
    ax.axhline(600, ls=":", color="gray", alpha=0.7, label="10 min")

    ax.set_xlabel("pin nodes (n_pin × n_axial)")
    ax.set_ylabel("Dymola end-to-end wall [s]")
    ax.set_title("17×17 PWR assembly stress test — Dymola scaling")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()

    out = os.path.join(REPO_ROOT, "results", "stress_assembly_17x17.png")
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"wrote {out}")
    print(f"final wall times: {list(zip(labels, walls))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
