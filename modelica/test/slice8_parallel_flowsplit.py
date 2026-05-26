"""Slice 8 — parallel-channel momentum + flow-split (the across/through coupling).

Verifies ṁ_i = √(Δp / K_i) to machine precision across 3 channels with
different K. Same scenario as soultest-julia slice 8 — the case netflow
flagged as genuinely hard (friction Jacobian singular at ṁ=0).
"""
from __future__ import annotations

import math
import sys

import DyMat

from dymola_harness import new_dymola, simulate


K = [1.0e8, 2.0e8, 4.0e8]
P_IN = 2.0e5
P_OUT = 1.0e5
DP = P_IN - P_OUT


def main() -> int:
    with new_dymola() as (dymola, work):
        mat = simulate(
            dymola, work,
            "NetflowModelica.Tests.ParallelChannelFlowSplit",
            stop_time=1.0, n_intervals=5,
            result_stem="slice8",
        )
        m = DyMat.DyMatFile(mat)

    mdot = [float(m.data(f"mdot{i}")[-1]) for i in (1, 2, 3)]
    mtot = float(m.data("mdot_total")[-1])
    analytic = [math.sqrt(DP / k) for k in K]

    print(" channel    K            ṁ (model)      ṁ analytic     |Δ|")
    max_err = 0.0
    for i, (mi, ki, ai) in enumerate(zip(mdot, K, analytic), start=1):
        e = abs(mi - ai)
        max_err = max(max_err, e)
        print(f"   {i}    {ki:.2e}    {mi:.10f}    {ai:.10f}    {e:.2e}")
    print(f"\n total ṁ = {mtot:.10f}    expected {sum(analytic):.10f}")
    print(f" max |Δ| = {max_err:.2e}")

    ok = max_err < 1e-8
    if ok:
        print("\nFLOW-SPLIT VERIFY PASS (ṁ_i = √(Δp/K_i) at machine precision)")
        return 0
    print("\nFLOW-SPLIT VERIFY FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
