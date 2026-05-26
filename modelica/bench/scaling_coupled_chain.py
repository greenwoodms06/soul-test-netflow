"""Scaling sweep — find Dymola's compile/translate wall on CoupledChain.

Anchored against Julia's MTK-F4 / MTK-F9 (~N^1.6 mtkcompile, ~25-40 min @
~17k unknowns extrapolated). Sweeps the axial-slice count n and times the
end-to-end simulateModel call (which does translate + compile + simulate).

Approximate per-N unknown count for CoupledChain:
  ~ 4·n nodal temperatures (centerline/ps/ci/co per slice)
  + 5·n medium variables (h, T, p, Q, state per cell)
  + connect()-emitted equations
  ≈ 10–15 per axial slice after mtkcompile/Dymola's reduction
"""
from __future__ import annotations

import json
import os
import sys
import time

from dymola_harness import new_dymola


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "results")


def measure_one(dymola, work, n: int) -> dict:
    """Time a single CoupledChain(n=N) simulate end-to-end."""
    result_stem = os.path.join(work, f"scaling_n{n}")

    # Modifier syntax overrides the parameter at the simulate-model call.
    t0 = time.perf_counter()
    ok = dymola.simulateModel(
        f"NetflowModelica.Tests.CoupledChain(n={n})",
        startTime=0.0, stopTime=1.0, numberOfIntervals=10,
        method="Dassl", tolerance=1e-6,
        resultFile=result_stem,
    )
    dt = time.perf_counter() - t0

    log = dymola.getLastErrorLog()
    n_unknowns = extract_unknowns(log)
    return {
        "n": n,
        "ok": bool(ok),
        "wall_s": dt,
        "n_unknowns": n_unknowns,
    }


def extract_unknowns(log: str) -> int | None:
    """Pull 'X scalar unknowns' from Dymola's translation report."""
    import re
    # Translation reports a 'Time-varying variables: N scalars' line and others;
    # the most direct count is from 'DAE has X scalar unknowns'.
    m = re.search(r"DAE has (\d+) scalar unknowns", log)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+) scalar unknowns", log)
    if m:
        return int(m.group(1))
    return None


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    sizes = [10, 100, 1000, 2500, 5000, 10000, 20000]
    rows: list[dict] = []
    with new_dymola() as (dymola, work):
        for n in sizes:
            print(f"--- N = {n} ---", flush=True)
            row = measure_one(dymola, work, n)
            print(
                f"  ok={row['ok']:<5}  wall={row['wall_s']:7.2f} s"
                f"  unknowns={row['n_unknowns']}",
                flush=True,
            )
            rows.append(row)
            # Break early if a single run takes more than 5 minutes — that's
            # already past the "user patience" wall.
            if row["wall_s"] > 300:
                print(f"\n[breaking sweep — N={n} took {row['wall_s']:.0f} s > 300 s wall]")
                break

    out_json = os.path.join(OUT_DIR, "scaling_coupled_chain.json")
    with open(out_json, "w") as f:
        json.dump(rows, f, indent=2)

    print("\nSummary:")
    print(f"  {'N':>6s}  {'unknowns':>9s}  {'wall [s]':>9s}  {'wall/N':>9s}")
    for r in rows:
        per_n = r["wall_s"] / r["n"] if r["n"] else 0
        print(f"  {r['n']:>6d}  {str(r['n_unknowns']):>9s}  {r['wall_s']:>9.2f}  {per_n:>9.4f}")

    # Estimate exponent if we have enough points
    import math
    valid = [r for r in rows if r["wall_s"] > 0]
    if len(valid) >= 3:
        # power-law fit on (n, wall_s): wall = a · n^p
        xs = [math.log(r["n"]) for r in valid[-3:]]
        ys = [math.log(r["wall_s"]) for r in valid[-3:]]
        # least-squares on the last 3 points
        n_pts = len(xs)
        sx = sum(xs); sy = sum(ys); sxx = sum(x*x for x in xs); sxy = sum(x*y for x,y in zip(xs,ys))
        p = (n_pts*sxy - sx*sy) / (n_pts*sxx - sx*sx)
        print(f"\n  apparent exponent on last 3 points: p ≈ {p:.2f}")
        print(f"  (Julia's MTK-F4 anchor: ~N^1.4–1.7 on mtkcompile)")
    print(f"\nwrote {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
