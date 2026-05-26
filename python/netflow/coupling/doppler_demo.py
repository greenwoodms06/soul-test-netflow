"""Reproducible generator for the honest Doppler-feedback figure.

Replaces an orphan figure that displayed a toy-slab reactivity magnitude the
papers withdrew as non-physical (see ADR-0001). The negative *sign* (inherent
stability) is real and is what the figure asserts; the *magnitude* on a 1-group
bare slab is illustrative only. The physical fuel-temperature Doppler coefficient
for fresh 3.10 wt% UO2 is ~-2 to -2.5 pcm/K (derived from VERA P1/P2 KENO
eigenvalues; see references/godfrey-2014-vera-spec).

Run:  python -m netflow.coupling.doppler_demo
"""

from __future__ import annotations

import numpy as np


def make_doppler_figure(out_path: str = "results/doppler_feedback.png") -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from netflow.coupling.neutronics_thermal import (
        solve_doppler_coupled, doppler_feedback_curve,
    )

    powers = np.linspace(0.0, 40e6, 9)            # W (toy 1-group slab)
    ks = doppler_feedback_curve(list(powers))
    rho = (ks - 1.0) / ks * 1e5                    # pcm
    rho = rho - rho[0]                             # change from cold

    cold = solve_doppler_coupled(power_W=0.0)
    hot = solve_doppler_coupled(power_W=40e6)
    x = np.linspace(0.0, 100.0, cold.flux.size)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4))

    ax1.plot(powers / 1e6, rho, "o-", color="#c0392b")
    ax1.axhline(0.0, ls="--", color="gray", lw=1)
    ax1.set_xlabel("reactor power (MW, toy slab)")
    ax1.set_ylabel("reactivity change (pcm)")
    ax1.set_title("Doppler feedback: negative slope = stable\n(SIGN is the result, not magnitude)")
    ax1.text(0.40, 0.92,
             "magnitude ILLUSTRATIVE (1-group bare slab).\n"
             "physical fuel-T Doppler ≈ -2 to -2.5 pcm/K\n"
             "(derived, VERA P1/P2 KENO)",
             transform=ax1.transAxes, ha="left", va="top", fontsize=8.5,
             bbox=dict(boxstyle="round", fc="#fdf2e9", ec="#c0392b"))

    ax2.plot(x, cold.flux / cold.flux.max(), label="cold (0 MW)", color="#2c6fbb")
    ax2.plot(x, hot.flux / hot.flux.max(), label="hot, Doppler-flattened", color="#c0392b")
    ax2.set_xlabel("position (cm)")
    ax2.set_ylabel("normalized flux")
    ax2.set_title("Self-consistent flux mode (power COMPUTED, not imposed)")
    ax2.legend(loc="lower center")

    fig.suptitle("Coupled neutronics↔thermal with Doppler feedback "
                 "— sign physical, magnitude illustrative (toy slab)",
                 fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out_path}", flush=True)


if __name__ == "__main__":
    make_doppler_figure()
