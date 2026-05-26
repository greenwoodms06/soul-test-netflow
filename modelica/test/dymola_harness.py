"""Headless-Dymola helper shared by slice tests.

Establishes the environment Dymola needs when launched directly from the
Python interface (bypassing the /usr/local/bin/dymola wrapper):
  - DYMOLA env var ($DYMOLA/bin/dsbuild.sh is invoked by name during compile)
  - LD_LIBRARY_PATH = Dymola's bundled libgit2 etc.

Then provides ``new_dymola(work)`` which yields a connected interface with the
working directory set, MSL pre-loaded, and the project's NetflowModelica package
loaded if present.
"""
from __future__ import annotations

import contextlib
import os
import shutil
import tempfile
from collections.abc import Iterator

_DYMOLA_ROOT = os.environ.get("DYMOLA_ROOT", "/opt/dymola-2026x-x86_64")
_MSL_PATH = os.environ.get(
    "DYMOLA_MSL",
    f"{_DYMOLA_ROOT}/Modelica/Library/Modelica 4.1.0/package.mo",
)
_DYMOLA_EXE = os.environ.get("DYMOLA_EXE", f"{_DYMOLA_ROOT}/bin64/dymola")

os.environ.setdefault("DYMOLA", _DYMOLA_ROOT)
_lib_extra = f"{_DYMOLA_ROOT}/bin/lib64:{_DYMOLA_ROOT}/bin/lib"
_lib_cur = os.environ.get("LD_LIBRARY_PATH", "")
os.environ["LD_LIBRARY_PATH"] = (
    f"{_lib_extra}:{_lib_cur}" if _lib_cur else _lib_extra
)

from dymola.dymola_interface import DymolaInterface  # noqa: E402

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_NETFLOW_PACKAGE = os.path.join(_PROJECT_ROOT, "NetflowModelica", "package.mo")


class DymolaError(RuntimeError):
    pass


@contextlib.contextmanager
def new_dymola(
    *,
    keep_workdir: bool = False,
    load_netflowmodelica: bool = True,
) -> Iterator[tuple[DymolaInterface, str]]:
    """Yield ``(dymola, workdir)`` with MSL (+ NetflowModelica) loaded.

    ``keep_workdir=True`` preserves the temp directory after exit; useful when
    debugging a failed slice.
    """
    work = tempfile.mkdtemp(prefix="dymola_slice_")
    dymola = DymolaInterface(dymolapath=_DYMOLA_EXE)
    try:
        # openModel(..., changeDirectory=True) overrides our cwd; load with
        # changeDirectory=False, then cd to the workdir explicitly. (Otherwise
        # relative resultFile paths land inside the MSL install directory.)
        if not dymola.openModel(_MSL_PATH, mustRead=True, changeDirectory=False):
            raise DymolaError(
                "openModel(MSL) failed:\n" + dymola.getLastErrorLog()
            )
        if load_netflowmodelica and os.path.isfile(_NETFLOW_PACKAGE):
            if not dymola.openModel(
                _NETFLOW_PACKAGE, mustRead=True, changeDirectory=False
            ):
                raise DymolaError(
                    "openModel(NetflowModelica) failed:\n"
                    + dymola.getLastErrorLog()
                )
        dymola.cd(work)
        # Default .mat is single-precision compressed; we want full double for
        # verification work where comparing model output to analytic at the
        # 1e-6 K level is the whole point.
        if not dymola.experimentSetupOutput(doublePrecision=True):
            raise DymolaError(
                "experimentSetupOutput(doublePrecision=True) failed:\n"
                + dymola.getLastErrorLog()
            )
        yield dymola, work
    finally:
        try:
            dymola.close()
        except Exception:
            pass
        if not keep_workdir:
            shutil.rmtree(work, ignore_errors=True)
        else:
            print(f"[harness] keeping workdir: {work}")


def simulate(
    dymola: DymolaInterface,
    work: str,
    model: str,
    *,
    stop_time: float = 1.0,
    start_time: float = 0.0,
    method: str = "Dassl",
    tolerance: float = 1e-6,
    n_intervals: int = 500,
    result_stem: str = "result",
) -> str:
    """Translate-and-simulate. Returns absolute path of the .mat result.

    Raises ``DymolaError`` on translation/compile/simulation failure.
    """
    result_path = os.path.join(work, result_stem)
    ok = dymola.simulateModel(
        model,
        startTime=start_time,
        stopTime=stop_time,
        numberOfIntervals=n_intervals,
        method=method,
        tolerance=tolerance,
        resultFile=result_path,
    )
    if not ok:
        raise DymolaError(
            f"simulateModel({model!r}) failed:\n" + dymola.getLastErrorLog()
        )
    mat = result_path + ".mat"
    if not os.path.isfile(mat):
        raise DymolaError(
            f"simulateModel({model!r}) returned True but no result at {mat!r}"
        )
    return mat
