"""Advanced-flag dogfood — step 2 of the 2026-05-26 unfreeze.

Closes the 'defaults-only' caveat in COMPARISON.md §6 by measuring how
Dymola's advanced flags move the wall time on a single 17x17xN assembly.

Strategy:
  1. SMALL-LADDER SWEEP @ 17×17×10 (~106 s baseline). Cheap enough to try
     several flag combinations. Sample winners.
  2. HEADLINE @ 17×17×30 (~397 s baseline). Two or three winners promoted
     here to give the COMPARISON.md headline update.

Verification: physics invariants from verify_assembly_physics.py
(Q_total = 19,039,320 W exactly; T_cool_outlet_max in 600-615 K band;
T_centerline_hot ≈ 1265 K). A flag that breaks physics doesn't count as
faster.

MSL-only (per ADR-0002): all flags are Dymola-side (Advanced.* / Hidden.*),
no third-party library swap-ins.
"""
from __future__ import annotations

import json
import os
import sys
import time

from dymola_harness import new_dymola, DymolaError


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "results")


# Each entry: (label, list of ExecuteCommand strings BEFORE simulateModel,
#              method= for simulateModel, tolerance=).
# `default` is the baseline that produced the 397 s headline.
SCENARIOS = [
    ("default",                  [],                                                "Dassl",     1e-6),
    ("sparse",                   ["Advanced.Translation.SparseActivate = true"],                "Dassl",     1e-6),
    ("sparse+cvode",             ["Advanced.Translation.SparseActivate = true"],                "Cvode",     1e-6),
    ("sparse+esdirk23a",         ["Advanced.Translation.SparseActivate = true"],                "Esdirk23a", 1e-6),
    ("sparse+radauiia",          ["Advanced.Translation.SparseActivate = true"],                "RadauIIa",  1e-6),
    ("sparse+parallel",          ["Advanced.Translation.SparseActivate = true",
                                  "Advanced.ParallelizeCode = true"],               "Dassl",     1e-6),
    ("looser_tol",               [],                                                "Dassl",     1e-4),
    ("sparse+looser",            ["Advanced.Translation.SparseActivate = true"],                "Dassl",     1e-4),
]


# Physics invariants (from test/verify_assembly_physics.py)
def _check_physics(m, n_pin: int, n_axial: int) -> dict:
    import DyMat
    Q_expected = n_pin * 18000 * 3.66
    Q = float(m.data("Q_total_assembly")[-1])
    T_cool = float(m.data("T_cool_outlet_max")[-1])
    T_cl = float(m.data("T_centerline_hot")[-1])

    ok = (
        abs(Q - Q_expected) < 1.0
        and 600.0 <= T_cool <= 615.0
        and 1240.0 <= T_cl <= 1290.0
    )
    return {
        "Q_total": Q,
        "T_cool_outlet_max": T_cool,
        "T_centerline_hot": T_cl,
        "physics_ok": ok,
    }


def _set_flags(dymola, flags: list[str]) -> None:
    # ExecuteCommand returns False even on rename-warnings in Dymola 2026x.
    # Verify the flag stuck by reading it back.
    for f in flags:
        dymola.ExecuteCommand(f)
        # Best-effort: try to read back; if not "true", report.
        name = f.split("=")[0].strip()
        readback = dymola.ExecuteCommand(name)
        log = dymola.getLastErrorLog()
        if "true" not in log.lower() and readback is False:
            # Couldn't verify — print log, keep going.
            print(f"   [flag-check] {name}: log={log[:150]!r}", flush=True)


def measure(dymola, work, n_pin: int, n_axial: int,
            label: str, flags: list[str], method: str, tolerance: float) -> dict:
    import DyMat
    stem = os.path.join(work, f"flag_{label}_{n_pin}_{n_axial}")
    # Reset flags first (idempotent) — we re-set on every run so order doesn't matter.
    dymola.ExecuteCommand("Advanced.Translation.SparseActivate = false")
    dymola.ExecuteCommand("Advanced.ParallelizeCode = false")
    _set_flags(dymola, flags)

    t0 = time.perf_counter()
    ok = dymola.simulateModel(
        f"NetflowModelica.Tests.Assembly17x17(n_pin={n_pin}, n_axial={n_axial})",
        startTime=0.0, stopTime=1.0, numberOfIntervals=5,
        method=method, tolerance=tolerance, resultFile=stem,
    )
    dt = time.perf_counter() - t0
    row = {
        "label": label, "flags": flags, "method": method, "tolerance": tolerance,
        "n_pin": n_pin, "n_axial": n_axial,
        "ok": bool(ok), "wall_s": dt,
    }
    if ok and os.path.isfile(stem + ".mat"):
        try:
            m = DyMat.DyMatFile(stem + ".mat")
            row.update(_check_physics(m, n_pin, n_axial))
        except Exception as e:  # noqa: BLE001
            row["physics_ok"] = False
            row["error"] = str(e)
    else:
        row["physics_ok"] = False
        row["error"] = dymola.getLastErrorLog()[:400]
    return row


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    rows: list[dict] = []
    # Small ladder first
    with new_dymola() as (dymola, work):
        # Step 2a — 17×17×10 sweep
        for label, flags, method, tol in SCENARIOS:
            print(f"[10] {label:18s}  method={method:10s} tol={tol:.0e}  flags={flags}",
                  flush=True)
            try:
                r = measure(dymola, work, n_pin=17*17, n_axial=10,
                            label=label, flags=flags, method=method, tolerance=tol)
            except Exception as e:  # noqa: BLE001
                r = {"label": label, "flags": flags, "method": method, "tolerance": tol,
                     "n_pin": 17*17, "n_axial": 10, "ok": False, "physics_ok": False,
                     "wall_s": float("nan"), "error": str(e)[:400]}
            tag = "OK" if r.get("physics_ok") else "BAD" if r.get("ok") else "FAIL"
            print(f"   -> {tag:4s}  wall={r['wall_s']:7.2f} s   "
                  f"Tcl={r.get('T_centerline_hot', float('nan')):.2f} K", flush=True)
            rows.append(r)

    out_json = os.path.join(OUT_DIR, "advanced_flag_sweep_17x17_10.json")
    with open(out_json, "w") as f:
        json.dump(rows, f, indent=2)
    print(f"\nwrote {out_json}", flush=True)

    # Pick winners (physics_ok and within 1.5x of best wall time)
    ok_rows = [r for r in rows if r.get("physics_ok") and r.get("ok")]
    if not ok_rows:
        print("[abort] no physics-OK rows at 17×17×10", flush=True)
        return 1
    best_wall = min(r["wall_s"] for r in ok_rows)
    winners = [r for r in ok_rows if r["wall_s"] <= 1.5 * best_wall][:3]
    print(f"\n[promoting to 17×17×30] best={best_wall:.1f}s, "
          f"promoting {[w['label'] for w in winners]}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
