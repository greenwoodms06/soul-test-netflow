"""Subchannel-resolved coupled hydraulic <-> thermal solve.

Pushes the generic core to coupled subchannel T-H — the realistic
mechanism behind the VERA coolant-spread gap (§28). Built entirely on
the public core + the hydraulic and thermal plugins, orchestrated here
in the coupling layer (allowed to import multiple plugins).

Physics captured:
  * 3D subchannel pressure field: each pin-position channel has axial
    flow segments AND lateral cross-flow to its 4 neighbors.
  * Guide-tube channels have larger flow area -> lower axial resistance
    -> carry bypass flow, pulling flow away from neighboring fuel
    channels (which then run hotter). This is the spatial spread the
    diffusive-mixing model could not produce.
  * Picard coupling: thermal T -> coolant density -> hydraulic K ->
    flow distribution -> thermal advection. Mirrors MC21/CTF.

NOT captured (honest scope): turbulent-mixing correlations, grid form
losses, lateral momentum closure. So the spread is captured
*mechanistically* and largely, but exact VERA match would need
calibrated correlations — this is a generic-solver reach demonstration,
not a CTF replacement.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from netflow import Network, Node
from netflow.plugins.hydraulic import Pipe


# ---- geometry / operating point (VERA-ish) ----
R_PELLET = 4.096e-3
R_CLAD_OUTER = 4.750e-3
PITCH = 12.6e-3
ROD_OD = 2 * R_CLAD_OUTER
CP = 5500.0
T_INLET = 565.0          # K
P_DROP = 1.5e5           # Pa nominal assembly pressure drop
GAP_COND = 7500.0        # W/m2K empirical gap conductance


def water_density(T_K: float) -> float:
    return 745.0 - 1.55 * (T_K - 565.0)


@dataclass
class SubchannelResult:
    coolant_exit: np.ndarray     # (N,N) K
    fuel_centerline: np.ndarray  # (N,N) K  (peak over axial)
    channel_flow: np.ndarray     # (N,N) kg/s axial mass flow
    n_picard: int
    converged: bool
    spread_K: float
    coolant_axial: np.ndarray | None = None   # (N,N,n_ax) K, full field


def _solve_hydraulic(N, n_ax, guide, T_mean_field, total_mdot,
                     guide_K=0.25, K_lat=50.0):
    """3D subchannel pressure-flow solve. Returns per-channel axial mass
    flow (N,N) summed over the channel (the channel throughput).

    ``guide_K`` is the guide-tube axial resistance relative to fuel
    channels (lower = more bypass). ``K_lat`` is the lateral cross-flow
    resistance (higher = more isolated channels). Both are the calibrated
    parameters that, in a real subchannel code, come from turbulent-
    mixing and form-loss correlations.
    """
    net = Network()
    # pressure nodes p[i,j,k], k=0..n_ax (n_ax+1 levels)
    def pid(i, j, k):
        return f"p_{i}_{j}_{k}"
    # inlet plenum (k=0) fixed high P; outlet plenum (k=n_ax) fixed 0
    for i in range(N):
        for j in range(N):
            for k in range(n_ax + 1):
                if k == 0:
                    net.add_node(Node(id=pid(i, j, k), fixed=P_DROP))
                elif k == n_ax:
                    net.add_node(Node(id=pid(i, j, k), fixed=0.0))
                else:
                    net.add_node(Node(id=pid(i, j, k)))
    # axial pipes
    axial_edges = {}
    for i in range(N):
        for j in range(N):
            is_guide = (i, j) in guide
            # guide tube resistance relative to fuel channel (calibrated)
            base_K = guide_K if is_guide else 1.0
            T_mean = T_mean_field[i, j]
            rho = water_density(T_mean)
            K_seg = base_K * (745.0 / rho) / n_ax   # per segment
            for k in range(n_ax):
                e = Pipe(pid(i, j, k), pid(i, j, k + 1), K=max(K_seg, 1e-6))
                net.add_edge(e)
                axial_edges.setdefault((i, j), []).append(e)
    # lateral cross-flow pipes at interior levels (high resistance)
    for i in range(N):
        for j in range(N):
            for k in range(1, n_ax):
                if i + 1 < N:
                    net.add_edge(Pipe(pid(i, j, k), pid(i + 1, j, k), K=K_lat))
                if j + 1 < N:
                    net.add_edge(Pipe(pid(i, j, k), pid(i, j + 1, k), K=K_lat))
    res = net.solve_steady(method="newton", tol=1e-9, max_iter=200)
    # channel throughput = axial flow in the first segment (volumetric);
    # convert to mass flow with inlet density, then normalize to total_mdot
    vol_flow = np.zeros((N, N))
    for (i, j), edges in axial_edges.items():
        vol_flow[i, j] = res.edge_flux(edges[0])
    mass_flow = vol_flow * water_density(T_INLET)
    # normalize so total matches the imposed assembly mass flow
    mass_flow *= total_mdot / mass_flow.sum()
    return mass_flow, res.converged


def _solve_thermal(N, n_ax, q_map, mass_flow, guide, lateral_mix_frac=0.05):
    """Per-channel coolant + fuel solve given the channel mass flows.

    Coolant: axial advection (CoolantAdvection) + lateral enthalpy
    exchange (CoolantMixing) between adjacent channels. Fuel centerline
    from a lumped gap+conduction estimate.
    """
    from netflow.plugins.thermal import (
        CoolantAdvection, CoolantMixing, ContactResistance,
    )
    net = Network()
    L = 3.658
    dz = L / n_ax

    def cool(i, j, k):
        return f"c_{i}_{j}_{k}"

    # coolant nodes + inlet/outlet per channel
    for i in range(N):
        for j in range(N):
            net.add_node(Node(id=f"in_{i}_{j}", fixed=T_INLET))
            net.add_node(Node(id=f"out_{i}_{j}", fixed=T_INLET))
            for k in range(n_ax):
                # heat into this slice (0 for guide tubes)
                q_slice = 0.0 if (i, j) in guide else q_map[i, j] * dz
                net.add_node(Node(id=cool(i, j, k), source=q_slice,
                                  state0=T_INLET + 20))
    # axial advection chain per channel
    for i in range(N):
        for j in range(N):
            mdot = max(mass_flow[i, j], 1e-6)
            prev = f"in_{i}_{j}"
            for k in range(n_ax):
                net.add_edge(CoolantAdvection(prev, cool(i, j, k),
                                              mdot=mdot, cp=CP))
                prev = cool(i, j, k)
            net.add_edge(CoolantAdvection(prev, f"out_{i}_{j}",
                                          mdot=mdot, cp=CP))
    # lateral enthalpy exchange between adjacent channels at each level
    for i in range(N):
        for j in range(N):
            for k in range(n_ax):
                m_mix = lateral_mix_frac * max(mass_flow[i, j], 1e-6)
                if i + 1 < N:
                    net.add_edge(CoolantMixing(cool(i, j, k), cool(i + 1, j, k),
                                               mdot_mix=m_mix, cp=CP))
                if j + 1 < N:
                    net.add_edge(CoolantMixing(cool(i, j, k), cool(i, j + 1, k),
                                               mdot_mix=m_mix, cp=CP))
    res = net.solve_steady(method="newton", tol=1e-6, max_iter=80)
    coolant_exit = np.zeros((N, N))
    coolant_axial = np.zeros((N, N, n_ax))
    for i in range(N):
        for j in range(N):
            for k in range(n_ax):
                coolant_axial[i, j, k] = res.states[cool(i, j, k)]
            coolant_exit[i, j] = coolant_axial[i, j, n_ax - 1]
    return coolant_exit, res.converged, coolant_axial


def solve_coupled_subchannel(N, n_ax, q_map, guide, total_mdot,
                             max_picard=12, tol=0.05,
                             guide_K=0.25, K_lat=50.0, lateral_mix_frac=0.05):
    """Picard-couple subchannel hydraulics with the thermal solve.

    ``guide_K``, ``K_lat``, ``lateral_mix_frac`` are the calibrated
    cross-flow parameters (analogous to a subchannel code's mixing
    coefficients).
    """
    T_mean = np.full((N, N), T_INLET + 20.0)
    coolant_exit = np.full((N, N), T_INLET)
    converged = False
    coolant_axial = None
    for it in range(max_picard):
        mass_flow, hyd_ok = _solve_hydraulic(N, n_ax, guide, T_mean, total_mdot,
                                             guide_K=guide_K, K_lat=K_lat)
        new_cool, th_ok, coolant_axial = _solve_thermal(
            N, n_ax, q_map, mass_flow, guide, lateral_mix_frac=lateral_mix_frac)
        delta = float(np.max(np.abs(new_cool - coolant_exit)))
        coolant_exit = new_cool
        T_mean = 0.5 * (T_INLET + coolant_exit)
        if delta < tol:
            converged = hyd_ok and th_ok
            break

    # fuel centerline estimate (gap + clad + pellet) on top of coolant
    fuel_cl = np.full((N, N), np.nan)
    A_gap = 2 * math.pi * R_PELLET * 3.658
    sigma_dummy = 0.0
    for i in range(N):
        for j in range(N):
            if (i, j) in guide:
                continue
            qp = q_map[i, j]
            # film + clad + gap + fuel rises (lumped, peak axial ~1.5x avg)
            qp_peak = qp * 1.5
            dT_gap = qp_peak / (GAP_COND * (A_gap / 3.658))   # per-length basis
            dT_fuel = qp_peak / (4 * math.pi * 3.0)
            dT_clad = qp_peak * math.log(4.75 / 4.185) / (2 * math.pi * 17.0)
            dT_film = qp_peak / (2 * math.pi * R_CLAD_OUTER * 34000.0)
            fuel_cl[i, j] = (coolant_exit[i, j] + dT_film + dT_clad
                             + dT_gap + dT_fuel)

    spread = float(np.nanmax(coolant_exit) - np.nanmin(coolant_exit))
    return SubchannelResult(
        coolant_exit=coolant_exit, fuel_centerline=fuel_cl,
        channel_flow=mass_flow, n_picard=it + 1,
        converged=converged, spread_K=spread,
        coolant_axial=coolant_axial,
    )


# Standard 17x17 Westinghouse guide-tube positions
GUIDE_17 = {
    (2,5),(2,8),(2,11),(3,3),(3,13),
    (5,2),(5,5),(5,8),(5,11),(5,14),
    (8,2),(8,5),(8,8),(8,11),(8,14),
    (11,2),(11,5),(11,8),(11,11),(11,14),
    (13,3),(13,13),(14,5),(14,8),(14,11),
}
