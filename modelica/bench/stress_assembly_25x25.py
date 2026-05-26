"""25×25×30 stress test — step 4 of the 2026-05-26 unfreeze.

Pushes past Julia's 17×17×30 anchor to see whether Dymola's wall (gcc cc1
at 11.7 GB at 17×17×30) holds, slides, or hits the 16 GB RAM ceiling.

25×25 = 625 pin nodes per axial × 30 axial = 18,750 pin nodes (≈2.16× the
17×17×30 baseline). At the measured high-end exponent of 1.38, this
extrapolates to ~16-20 min wall time, with cc1 memory ~25 GB — likely OOM
on a 16 GB machine without `gcc -O0` or `tcc` mitigation.

Strategy:
  - Use the same Assembly17x17 model (n_pin is a parameter; the name is
    historical — works at any n_pin and n_axial).
  - Bracket with intermediate sizes (20×20, 22×22) before 25×25 so we don't
    lose ~20 min to an early OOM with no diagnostic.
  - Kill the run if any single step exceeds 1500 s (30 min) — past the
    ideas.md "comfortable region" boundary.
"""
from __future__ import annotations

import json
import os
import sys
import time

from dymola_harness import new_dymola


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def measure(dymola, work, n_pin: int, n_axial: int) -> dict:
    stem = os.path.join(work, f"asm_{n_pin}_{n_axial}")
    t0 = time.perf_counter()
    ok = dymola.simulateModel(
        f"NetflowModelica.Tests.Assembly17x17(n_pin={n_pin}, n_axial={n_axial})",
        startTime=0.0, stopTime=1.0, numberOfIntervals=5,
        method="Dassl", tolerance=1e-6, resultFile=stem,
    )
    dt = time.perf_counter() - t0
    return {"n_pin": n_pin, "n_axial": n_axial,
            "pin_nodes": n_pin * n_axial,
            "ok": bool(ok), "wall_s": dt}


def main() -> int:
    OUT_DIR = os.path.join(REPO_ROOT, "results")
    os.makedirs(OUT_DIR, exist_ok=True)
    # Climbing ladder past 17×17×30 (8,670 nodes / 397 s baseline).
    # 18×18×30 = 9,720 ; 20×20×30 = 12,000 ; 22×22×30 = 14,520 ; 25×25×30 = 18,750
    scenarios = [
        (18 * 18, 30),
        (20 * 20, 30),
        (22 * 22, 30),
        (25 * 25, 30),
    ]
    rows = []
    with new_dymola() as (dymola, work):
        for n_pin, n_axial in scenarios:
            print(f"--- n_pin={n_pin}  n_axial={n_axial}  "
                  f"(≈ {n_pin*n_axial} pin nodes) ---", flush=True)
            r = measure(dymola, work, n_pin, n_axial)
            print(f"  ok={r['ok']:<5}  wall={r['wall_s']:7.2f} s", flush=True)
            rows.append(r)
            if r["wall_s"] > 1500:
                print("\n[breaking — single run > 25 min wall]", flush=True)
                break
            if not r["ok"]:
                print("\n[breaking — failure (likely OOM or stall)]", flush=True)
                break

    out_json = os.path.join(OUT_DIR, "stress_assembly_25x25.json")
    with open(out_json, "w") as f:
        json.dump(rows, f, indent=2)
    print(f"\nwrote {out_json}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
