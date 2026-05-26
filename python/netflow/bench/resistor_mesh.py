"""Scaling benchmark: resistor mesh from 10² to 10⁴ nodes.

Run directly:

    python -m netflow.bench.resistor_mesh

Reports per-size: setup time, solve time, n_iter, memory if psutil is available.
"""

from __future__ import annotations

import gc
import time
from math import isqrt
from typing import Iterable

from netflow.demo import build_resistor_mesh


def _format_row(size: int, setup_s: float, solve_s: float, n_iter: int) -> str:
    return f"{size:>6d} | {setup_s:7.3f} s | {solve_s:7.3f} s | n_iter={n_iter}"


def run(sizes: Iterable[int] | None = None) -> list[dict]:
    """Run the benchmark over a list of square mesh sizes (N×N).

    Returns a list of dicts; also prints a table.
    """
    if sizes is None:
        sizes = [10, 32, 100]   # 100, ~1k, 10k nodes

    print(f"{'N×N':>6s} | {'setup':>9s} | {'solve':>9s} | iterations")
    print("-" * 50)

    results: list[dict] = []
    for N in sizes:
        gc.collect()
        t0 = time.perf_counter()
        net = build_resistor_mesh(rows=N, cols=N, R=1.0,
                                  left_state=1.0, right_state=0.0)
        setup_s = time.perf_counter() - t0
        t1 = time.perf_counter()
        res = net.solve_steady()
        solve_s = time.perf_counter() - t1
        print(_format_row(N * N, setup_s, solve_s, res.n_iter))
        results.append({
            "n_nodes": N * N,
            "setup_s": setup_s,
            "solve_s": solve_s,
            "n_iter": res.n_iter,
            "converged": res.converged,
        })

    return results


if __name__ == "__main__":
    run()
