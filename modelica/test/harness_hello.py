"""Hello-world Dymola headless harness check.

Two scenarios:
  (1) load + simulate an MSL example (proves MSL is reachable).
  (2) load + simulate a tiny user .mo (proves user packages compile through
      the same path the slice tests will use).

Both go through the shared helper in ``dymola_harness.py``; if this script
passes, slice tests can rely on ``new_dymola()`` to bring up a working
Dymola session.

Run:  .venv/bin/python test/harness_hello.py
"""
from __future__ import annotations

import os
import sys

import DyMat

from dymola_harness import DymolaError, new_dymola, simulate


def test_msl_example() -> None:
    with new_dymola(load_netflowmodelica=False) as (dymola, work):
        mat = simulate(
            dymola, work,
            "Modelica.Mechanics.Translational.Examples.PreLoad",
            stop_time=1.0, n_intervals=100,
            result_stem="msl_hello",
        )
        m = DyMat.DyMatFile(mat)
        names = m.names()
        # PreLoad's mass component is named "innerContactA"/etc.; pick whatever exists
        cand = next((n for n in ("spring.f", "friction.v_rel") if n in names), None)
        assert cand is not None, f"no expected signal in {len(names)} names"
        v = m.data(cand)
        assert len(v) > 0, f"empty {cand} trajectory"
        print(f"  [MSL] {len(names)} signals, {cand}[-1] = {v[-1]:.4f}")


def test_user_model() -> None:
    user_mo = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "harness_user_model.mo"
    )
    with new_dymola(load_netflowmodelica=False) as (dymola, work):
        if not dymola.openModel(user_mo):
            raise DymolaError(
                "openModel(user) failed:\n" + dymola.getLastErrorLog()
            )
        mat = simulate(
            dymola, work, "harness_user_model",
            stop_time=5.0, n_intervals=200, result_stem="user_hello",
        )
        m = DyMat.DyMatFile(mat)
        y = m.data("y")
        t = m.abscissa("y", valuesOnly=True)
        # tau=0.5, y_inf=1 → y(5) = 1 - exp(-10) ≈ 1.0 to <1e-4
        import math
        expected = 1.0 - math.exp(-t[-1] / 0.5)
        err = abs(y[-1] - expected)
        print(f"  [user] y({t[-1]:.2f}) = {y[-1]:.6f}, expected {expected:.6f}, |Δ|={err:.2e}")
        assert err < 1e-3, f"first-order response off by {err:.2e}"


def main() -> int:
    print("test 1: MSL example end-to-end")
    test_msl_example()
    print("test 2: user .mo end-to-end")
    test_user_model()
    print("harness OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
