"""Re-measure frozen netflow on THIS machine — do NOT trust the README's 1201.9 K
(carried guardrail: validation-vs-code-comparison). Reads /home/fig/soultest
(frozen); never modifies it. This is the baseline for the MTK-vs-netflow benchmark.
"""
import sys, time
sys.path.insert(0, "/home/fig/soultest")

from netflow import Network
from netflow.plugins.thermal import (
    FuelRod, ForcedConvection, CoolPropFluid, UO2, Zircaloy4, Helium_gap,
)
from netflow.core.node import Node


def netflow_quickstart():
    net = Network()
    rod = FuelRod(
        r_pellet=4.10e-3, gap_thickness=0.085e-3, r_clad_outer=4.75e-3, L=1.0,
        fuel_material=UO2(), clad_material=Zircaloy4(), gap_material=Helium_gap,
        gap_emissivity=0.85, q_lin=18_000.0,
    )
    ports = rod.build(net, prefix="rod_")
    net.add_node(Node(id="coolant", fixed=593.0))  # 320 C fixed
    net.add_edge(ForcedConvection(
        ports.clad_outer, "coolant",
        fluid=CoolPropFluid("Water", default_P=15.5e6),
        mdot=0.30, D_h=12.0e-3, A_ht=3.14e-2,
    ))
    t0 = time.perf_counter()
    res = net.solve_steady()
    dt = time.perf_counter() - t0
    return res.states[ports.centerline], dt, ports, net, res


if __name__ == "__main__":
    Tcl, dt, ports, net, res = netflow_quickstart()
    print(f"netflow centerline = {Tcl:.4f} K   (README quick-start says 1201.9 K)")
    print(f"solve time         = {dt*1e3:.2f} ms")
    # report the intermediate node temps so we can match netflow's closures in MTK
    print("node temperatures:")
    for k, v in res.states.items():
        print(f"  {k:24s} {v:10.4f} K")
