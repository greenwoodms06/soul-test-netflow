"""Re-measure the frozen netflow pin on THIS machine (SOUL-F-d guardrail).

Carries the lesson from the Julia attempt's findings: the netflow README is
stale (1201.9 K vs the actual ~1204.75 K netflow now solves to). Don't trust
the record — even the prior leg's re-measurement record. Re-run, capture the
numbers we'll compare against in slice 4.

Outputs the four node temperatures + solve time. Writes to results/
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, "/home/fig/soultest")

from netflow import Network
from netflow.core.node import Node
from netflow.plugins.thermal import (
    CoolPropFluid, ForcedConvection, FuelRod,
    Helium_gap, UO2, Zircaloy4,
)


def netflow_quickstart() -> tuple[dict[str, float], float]:
    net = Network()
    rod = FuelRod(
        r_pellet=4.10e-3, gap_thickness=0.085e-3, r_clad_outer=4.75e-3, L=1.0,
        fuel_material=UO2(), clad_material=Zircaloy4(), gap_material=Helium_gap,
        gap_emissivity=0.85, q_lin=18_000.0,
    )
    ports = rod.build(net, prefix="rod_")
    net.add_node(Node(id="coolant", fixed=593.0))
    net.add_edge(ForcedConvection(
        ports.clad_outer, "coolant",
        fluid=CoolPropFluid("Water", default_P=15.5e6),
        mdot=0.30, D_h=12.0e-3, A_ht=3.14e-2,
    ))
    t0 = time.perf_counter()
    res = net.solve_steady()
    dt = time.perf_counter() - t0
    nodes = {
        "centerline": res.states[ports.centerline],
        "pellet_surface": res.states[ports.pellet_surface],
        "clad_inner": res.states[ports.clad_inner],
        "clad_outer": res.states[ports.clad_outer],
        "coolant": res.states["coolant"],
    }
    return nodes, dt


def main() -> int:
    nodes, dt = netflow_quickstart()
    print("netflow re-measurement on this machine:")
    for k, v in nodes.items():
        print(f"  {k:<16s} {v:>10.4f} K")
    print(f"  solve time      {dt * 1e3:>10.2f} ms")
    print()
    print("Julia attempt (2026-05-21, same machine class):")
    print("  centerline       1204.7488 K")
    print("  pellet_surface    834.8303 K")
    print("  clad_inner        637.3277 K")
    print("  clad_outer        611.7027 K")
    print()
    # save baseline json for slice 4
    out_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "results",
        "netflow_baseline.json",
    )
    payload = {
        "nodes": nodes,
        "solve_time_s": dt,
        "scenario": "netflow_quickstart_PWR_pin_18kW_per_m_593K_coolant_15p5MPa",
    }
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
