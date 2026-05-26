"""Render the CoupledChain scaling sweep + Julia anchor for the FINDINGS plot."""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    with open(os.path.join(REPO_ROOT, "results", "scaling_coupled_chain.json")) as f:
        data = json.load(f)

    # combine both sweeps
    rows = data["rows_first_sweep_complete"] + data["rows_second_sweep_higher"]
    # dedupe by N keeping the largest
    by_n: dict[int, dict] = {}
    for r in rows:
        if r.get("wall_s") is None:
            continue
        n = r["n"]
        if n not in by_n or r["wall_s"] > by_n[n]["wall_s"]:
            by_n[n] = r
    sorted_rows = sorted(by_n.values(), key=lambda r: r["n"])

    Ns = [r["n"] for r in sorted_rows]
    walls = [r["wall_s"] for r in sorted_rows]
    unks = [r["unknowns"] for r in sorted_rows]

    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    ax.loglog(unks, walls, "o-", color="tab:blue", label="Dymola: CoupledChain(N) end-to-end")

    # Julia MTK-F4/F9 anchor — extrapolated point at "100 pins per-component" = 2k unknowns, 71 s
    ax.loglog([2000], [71], "s", color="tab:red", markersize=10,
              label="Julia MTK-F9: mtkcompile alone @ 100 pins (2k unk)")
    # Julia's extrapolated wall: 25-40 min at 17k unknowns
    ax.fill_betweenx([25 * 60, 40 * 60], 1.5e4, 2e4, color="tab:red", alpha=0.2,
                     label="Julia extrapolated mtkcompile @ ~17k (25–40 min)")

    # mark Dymola's wall (N=5000 killed at 10 min in dymosim — codegen finished)
    ax.axhline(10 * 60, ls=":", color="black", alpha=0.4)
    ax.text(3e5, 10 * 60, "N=5000 dymosim still running\nat 10 min (init solver wall)",
            fontsize=9, va="bottom", ha="right", color="gray")

    # Try to overlay 17x17 assembly data if available
    try:
        with open(os.path.join(REPO_ROOT, "results", "stress_assembly_17x17.json")) as f:
            asm = json.load(f)
        asm_unk = [r["n_pin"] * r["n_axial"] * 6 for r in asm if r.get("ok") and r.get("wall_s")]
        asm_walls = [r["wall_s"] for r in asm if r.get("ok") and r.get("wall_s")]
        asm_labels = [f"{r['n_pin']}×{r['n_axial']}" for r in asm if r.get("ok") and r.get("wall_s")]
        if asm_unk:
            ax.loglog(asm_unk, asm_walls, "^-", color="tab:green",
                      label="Dymola: 17×17 PWR assembly (n_pin × n_axial)")
            for x, y, lbl in zip(asm_unk, asm_walls, asm_labels):
                ax.annotate(lbl, (x, y), textcoords="offset points", xytext=(8, 4),
                            fontsize=8, color="tab:green")
    except FileNotFoundError:
        pass

    ax.set_xlabel("Unknowns")
    ax.set_ylabel("Wall time [s]")
    ax.set_title("CoupledChain scaling: Dymola end-to-end vs Julia MTK anchor")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="upper left", fontsize=9)
    fig.tight_layout()

    out = os.path.join(REPO_ROOT, "results", "scaling_coupled_chain.png")
    fig.savefig(out, dpi=120)
    plt.close(fig)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
