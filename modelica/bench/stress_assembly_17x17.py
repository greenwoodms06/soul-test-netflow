"""17×17 PWR assembly stress test — does Dymola hit Julia's wall?

Julia MTK-F9 anchored: mtkcompile alone was ~71 s @ 100 pins (2k unknowns)
with exponent ~N^1.6; extrapolated 25-40 min mtkcompile @ 17×17×30 ≈ 17k pin
nodes (~40k unknowns).

Reports end-to-end wall and indication of where time was spent.
Designed to be killable: starts with smaller assemblies and grows.
"""
from __future__ import annotations

import json
import os
import sys
import time

from dymola_harness import new_dymola


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def measure(dymola, work, n_pin: int, n_axial: int) -> dict:
    stem = os.path.join(work, f"assembly_p{n_pin}_z{n_axial}")
    t0 = time.perf_counter()
    ok = dymola.simulateModel(
        f"NetflowModelica.Tests.Assembly17x17(n_pin={n_pin}, n_axial={n_axial})",
        startTime=0.0, stopTime=1.0, numberOfIntervals=5,
        method="Dassl", tolerance=1e-6, resultFile=stem,
    )
    dt = time.perf_counter() - t0
    return {"n_pin": n_pin, "n_axial": n_axial, "ok": bool(ok), "wall_s": dt}


def main() -> int:
    OUT_DIR = os.path.join(REPO_ROOT, "results")
    os.makedirs(OUT_DIR, exist_ok=True)
    # Ladder: 4x4×10 (160 pin nodes), 8x8×10, 8x8×20, 17×17×10, 17×17×20, 17×17×30
    # Each step is roughly 2-4× the previous unknown count.
    scenarios = [
        (4 * 4, 10),
        (8 * 8, 10),
        (8 * 8, 20),
        (17 * 17, 10),
        (17 * 17, 20),
        (17 * 17, 30),
    ]
    rows: list[dict] = []
    with new_dymola() as (dymola, work):
        for n_pin, n_axial in scenarios:
            print(f"--- n_pin={n_pin}  n_axial={n_axial}  (≈ {n_pin*n_axial} pin nodes) ---", flush=True)
            r = measure(dymola, work, n_pin, n_axial)
            print(f"  ok={r['ok']:<5}  wall={r['wall_s']:7.2f} s", flush=True)
            rows.append(r)
            if r["wall_s"] > 600:
                print("\n[breaking — single run > 10 min wall]")
                break

    out_json = os.path.join(OUT_DIR, "stress_assembly_17x17.json")
    with open(out_json, "w") as f:
        json.dump(rows, f, indent=2)
    print(f"\nwrote {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
