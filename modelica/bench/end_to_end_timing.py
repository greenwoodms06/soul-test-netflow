"""Wall-clock timing of the slice-4 'match netflow' scenario through Dymola.

The user experience is:
  * Python imports + Dymola startup
  * openModel(MSL) + openModel(NetflowModelica)
  * simulateModel (= translate + compile + simulate)
  * read .mat

netflow's 9 ms is the pure Newton-solve time; Modelica's wall-clock includes
the translate/compile pipeline that buys you generated C, an integrator family,
and reusability. This timing makes the trade-off concrete.
"""
from __future__ import annotations

import sys
import time

from dymola_harness import new_dymola, simulate


def main() -> int:
    t0 = time.perf_counter()

    t_start_dymola = time.perf_counter()
    with new_dymola() as (dymola, work):
        t_dymola_ready = time.perf_counter()
        t_sim_start = time.perf_counter()
        simulate(
            dymola, work,
            "NetflowModelica.Tests.SinglePinNetflowMatch",
            stop_time=1.0, n_intervals=10, result_stem="timing",
        )
        t_sim_done = time.perf_counter()

    t_end = time.perf_counter()
    print(f"Dymola startup + MSL/Netflow load   = {t_dymola_ready - t_start_dymola:7.3f} s")
    print(f"simulateModel (translate+compile+sim) = {t_sim_done - t_sim_start:7.3f} s")
    print(f"total end-to-end                     = {t_end - t0:7.3f} s")
    print()
    print(f"netflow comparison (single-pin same scenario, just Newton): ~9 ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
