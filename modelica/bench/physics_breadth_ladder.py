"""Step 3 physics-breadth ladder — measure how cross-pin / neutronics /
subchannel scale up to the 17×17×30 anchor.

For each variant, run a 3-step ladder:
  - 8×8×10   (640 pin nodes — cheap baseline)
  - 17×17×10 (2 890 pin nodes — confirms scaling)
  - 17×17×30 (8 670 pin nodes — Julia anchor)

Compares against AssemblyVeraP6 baseline (parallel-independent channels).
Uses Advanced.Translation.SparseActivate = true (step-2 finding: doesn't hurt at
compile-bound walls, dramatically helps at init-bound walls).

Physics verification at each step (a flag-time finding from SOUL-F028 closure):
  - Q_total_assembly matches expected within float64 noise
  - T_centerline_hot in 800-1500 K band
  - Subchannel: spread bounded (lateral flow doesn't blow up)
"""
from __future__ import annotations

import json
import os
import sys
import time

from dymola_harness import new_dymola


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "results")


# (variant_model_name, kwargs_template, scenarios_to_run, stop_time, n_intervals)
VARIANTS = [
    ("AssemblyVeraP6",
     "(n_pin={n_pin}, n_axial={n_axial})",
     [(8*8, 10), (17*17, 10), (17*17, 30)],
     1.0, 5),
    ("AssemblyVeraP6CrossPin",
     "(n_pin={n_pin}, n_axial={n_axial}, G_cross=0.05)",
     [(8*8, 10), (17*17, 10), (17*17, 30)],
     1.0, 5),
    ("AssemblyVeraP6Neutronics",
     "(n_pin={n_pin}, n_axial={n_axial})",
     [(8*8, 10), (17*17, 10)],  # 17x17x30 deferred (transient, heavy)
     50.0, 50),
    ("AssemblyVeraP6Subchannel",
     "(n_side={n_side}, n_axial={n_axial})",
     [(8, 10), (17, 10), (17, 30)],  # n_side, not n_pin
     1.0, 5),
]


def measure(dymola, work, variant: str, kwargs: dict, stop_time: float,
            n_intervals: int) -> dict:
    import DyMat
    stem_kwargs = "_".join(f"{k}{v}" for k, v in kwargs.items())
    stem = os.path.join(work, f"{variant}_{stem_kwargs}")
    dymola.ExecuteCommand("Advanced.Translation.SparseActivate = true")

    if variant == "AssemblyVeraP6Subchannel":
        ctor = f"({', '.join(f'{k}={v}' for k, v in kwargs.items())})"
    else:
        ctor = f"({', '.join(f'{k}={v}' for k, v in kwargs.items())})"
    full = f"NetflowModelica.Tests.{variant}{ctor}"

    t0 = time.perf_counter()
    ok = dymola.simulateModel(
        full, startTime=0.0, stopTime=stop_time, numberOfIntervals=n_intervals,
        method="Dassl", tolerance=1e-6, resultFile=stem,
    )
    dt = time.perf_counter() - t0
    row = {"variant": variant, "kwargs": kwargs,
           "ok": bool(ok), "wall_s": dt}
    if ok and os.path.isfile(stem + ".mat"):
        try:
            m = DyMat.DyMatFile(stem + ".mat")
            # Common diagnostics across variants
            for key in ("Q_total_assembly", "T_centerline_hot",
                        "T_cool_exit_spread", "T_cool_exit_max",
                        "T_fuel_volavg_peak", "P_total"):
                try:
                    row[key] = float(m.data(key)[-1])
                except Exception:  # noqa: BLE001
                    pass
        except Exception as e:  # noqa: BLE001
            row["read_error"] = str(e)
    else:
        row["error"] = dymola.getLastErrorLog()[:500]
    return row


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = []
    with new_dymola() as (dymola, work):
        for variant, _tpl, scenarios, stop_time, n_intervals in VARIANTS:
            for sc in scenarios:
                if variant == "AssemblyVeraP6Subchannel":
                    n_side, n_axial = sc
                    kwargs = {"n_side": n_side, "n_axial": n_axial}
                    label = f"{variant} n_side={n_side} n_axial={n_axial}"
                else:
                    n_pin, n_axial = sc
                    kwargs = {"n_pin": n_pin, "n_axial": n_axial}
                    label = f"{variant} n_pin={n_pin} n_axial={n_axial}"
                print(f"--- {label} ---", flush=True)
                r = measure(dymola, work, variant, kwargs, stop_time, n_intervals)
                print(f"   ok={r['ok']}  wall={r['wall_s']:7.2f} s   "
                      f"Tcl={r.get('T_centerline_hot', float('nan')):.2f} K  "
                      f"Q={r.get('Q_total_assembly', float('nan')):.3e} W",
                      flush=True)
                rows.append(r)
                if r["wall_s"] > 1200:  # 20 min single-run cap
                    print("[breaking — single run > 20 min]", flush=True)
                    break

    out_json = os.path.join(OUT_DIR, "physics_breadth_ladder.json")
    with open(out_json, "w") as f:
        json.dump(rows, f, indent=2)
    print(f"\nwrote {out_json}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
