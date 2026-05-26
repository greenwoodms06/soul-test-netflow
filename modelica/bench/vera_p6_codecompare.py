"""VERA P6 code-comparison — actually consume the Step 1 anchor.

Apply Kelly 2017's measured radial peaking pattern (range ~0.96–1.05 across
the 1/4-assembly, cosine-from-centre shape, all-fuel-positions; per netflow's
vera_codecompare.py the spread is geometry-dominated by guide-tube bypass,
not power-dominated) to AssemblyVeraP6 at 17×17×30 and read the resulting
outlet-T distribution.

Code-comparison reported against:
  - Kelly 2017 Fig. 11 subchannel exit coolant spread: 6.6 K (CTF/VERA), 8.7 K
    (COBRA-IE). NOTE: this is geometry-driven (guide-tube bypass). This leg's
    model has NO guide tubes — all 289 positions are fuel rods — so the
    measured spread is power-driven only. The gap-to-Kelly is then a
    structural caveat about modeling choices, not a calibration failure.
  - Kelly 2017 Fig. 24: peak volume-average fuel pin T ≈ 1066 °C (P7 number).
    P6 hot-pin volavg is lower. We report this leg's peak.
  - Kelly 2017 Fig. 10: pin power factor range 0.96–1.05.

P6/P7 has no reference solution per Godfrey 2014; this is code-to-code
comparison, NOT validation.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

import DyMat
import numpy as np

from dymola_harness import new_dymola


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "results")


def vera_p6_radial_peaking(n_side: int = 17, peak: float = 1.05) -> np.ndarray:
    """Flat-ish cosine-from-centre power map; range 1.0 (edge) to `peak` (centre)."""
    cx = cy = (n_side - 1) / 2.0
    r_max = math.hypot(cx, cy)
    factor = np.zeros((n_side, n_side))
    for i in range(n_side):
        for j in range(n_side):
            r = math.hypot(i - cx, j - cy) / r_max
            # shape: 1 at centre, 0 at corner; peak adds (peak-1)*shape on top of 1.
            shape = math.cos(min(r, 1.0) * math.pi / 2.0)
            factor[i, j] = 1.0 + (peak - 1.0) * shape
    # Normalise so the mean is exactly 1 (preserves total assembly power)
    factor /= factor.mean()
    return factor


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    n_side = 17
    n_pin = n_side * n_side
    n_axial = 30

    factor_2d = vera_p6_radial_peaking(n_side)
    # AssemblyVeraP6 expects a 1D array q_lin_factor[n_pin]; flatten in row-major
    # (matches the (i-1)*n_side + j indexing used elsewhere).
    factor_1d = factor_2d.flatten()
    # Build the modifier string for simulateModel(...) — Modelica accepts
    # explicit array literals in the constructor args.
    factor_str = "{" + ",".join(f"{v:.10f}" for v in factor_1d) + "}"

    print(f"radial peaking: min={factor_2d.min():.4f}  max={factor_2d.max():.4f}  "
          f"range={factor_2d.max() - factor_2d.min():.4f}  (target 0.96..1.05)",
          flush=True)

    model = (
        f"NetflowModelica.Tests.AssemblyVeraP6"
        f"(n_pin={n_pin}, n_axial={n_axial}, q_lin_factor={factor_str})"
    )

    with new_dymola() as (dymola, work):
        dymola.ExecuteCommand("Advanced.Translation.SparseActivate = true")
        stem = os.path.join(work, "vera_p6_codecompare")
        t0 = time.perf_counter()
        ok = dymola.simulateModel(
            model, startTime=0.0, stopTime=1.0, numberOfIntervals=5,
            method="Dassl", tolerance=1e-6, resultFile=stem,
        )
        dt = time.perf_counter() - t0
        if not ok:
            print("FAIL:", dymola.getLastErrorLog()[:600], flush=True)
            return 1
        m = DyMat.DyMatFile(stem + ".mat")

    Q = float(m.data("Q_total_assembly")[-1])
    spread = float(m.data("T_cool_exit_spread")[-1])
    Tmax = float(m.data("T_cool_exit_max")[-1])
    Tmin = float(m.data("T_cool_exit_min")[-1])
    Tfuel = float(m.data("T_fuel_volavg_peak")[-1])

    # Per-channel outlet T (reconstruct 2D map for visual check)
    T_exit = np.zeros((n_side, n_side))
    for ip in range(n_pin):
        i = ip // n_side
        j = ip % n_side
        try:
            T_exit[i, j] = float(m.data(f"T_cool_exit[{ip + 1}]")[-1])
        except Exception:
            T_exit[i, j] = float("nan")

    Q_expected = 17838.0 * 3.6576 * n_pin  # mean q_lin × L × n_pin

    out = {
        "n_side": n_side, "n_axial": n_axial,
        "Q_total_W": Q, "Q_expected_W": Q_expected,
        "T_cool_exit_min_K": Tmin, "T_cool_exit_max_K": Tmax,
        "T_cool_exit_spread_K": spread,
        "T_fuel_volavg_peak_K": Tfuel,
        "T_fuel_volavg_peak_C": Tfuel - 273.15,
        "wall_s": dt,
        "peaking_range": [float(factor_2d.min()), float(factor_2d.max())],
        "kelly_2017_p6_spread_K_CTF_VERA": 6.6,
        "kelly_2017_p6_spread_K_COBRA_IE": 8.7,
        "kelly_2017_p7_peak_volavg_C": 1066.0,
        "structural_caveat": (
            "this leg has no guide tubes (all 289 positions fuel); "
            "Kelly's 6.6 K spread is geometry-driven by guide-tube bypass. "
            "this measured spread is power-driven only."
        ),
    }
    out_json = os.path.join(OUT_DIR, "vera_p6_codecompare.json")
    with open(out_json, "w") as f:
        json.dump(out, f, indent=2)

    print(f"\n=== VERA P6 code-comparison (17×17×30, radial peaking applied) ===")
    print(f"  Q_total_assembly  = {Q:.4e} W  (expected {Q_expected:.4e} W, peaking-normalised)")
    print(f"  T_cool_exit  min  = {Tmin:.2f} K")
    print(f"  T_cool_exit  max  = {Tmax:.2f} K")
    print(f"  T_cool_exit_SPREAD = {spread:.3f} K   (Kelly P6 CTF/VERA = 6.6 K, COBRA-IE = 8.7 K)")
    print(f"  T_fuel_volavg_peak = {Tfuel:.2f} K = {Tfuel - 273.15:.1f} °C   "
          f"(Kelly P7 = 1066 °C; this is P6 ~uniform-peaking, expect lower)")
    print(f"  wall_s = {dt:.1f}")
    print(f"\n  >>> structural caveat: NO guide tubes in this model — power-driven spread only.")
    print(f"      Kelly's 6.6 K is geometry-driven; an apples-to-apples comparison would need")
    print(f"      adding guide-tube bypass topology (a separate experiment).")
    print(f"\nwrote {out_json}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
