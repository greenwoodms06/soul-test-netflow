"""Test the Picard-coupled hydraulic<->thermal demonstration.

Validates that two plugins couple on the unchanged core: the hydraulic
solve distributes flow (guide-tube bypass), the thermal update sets exit
temperatures, and the Picard loop converges.
"""

import pytest

CoolProp = pytest.importorskip("CoolProp")  # example imports thermal plugin chain

from netflow.coupling.coupled_th import (
    build_channels, solve_coupled, TOTAL_MDOT,
)


def test_picard_coupling_converges():
    channels = build_channels(n_fuel=7, guide_positions={2, 6}, q_pin=60000.0)
    mdot, T_exit, n_pic, converged, history = solve_coupled(channels, coupled=True)
    assert converged
    assert n_pic <= 30
    # History should be monotone-ish decreasing to tolerance
    assert history[-1] < 1e-5


def test_guide_tubes_carry_bypass_flow():
    """Guide-tube channels (lower K, larger area) must carry MORE flow
    than fuel channels."""
    channels = build_channels(n_fuel=7, guide_positions={2, 6}, q_pin=60000.0)
    mdot, _, _, _, _ = solve_coupled(channels, coupled=True)
    guide_flow = mdot["ch2"]
    fuel_flow = mdot["ch0"]
    assert guide_flow > fuel_flow
    # Mass conservation: all channel flows sum to total
    assert abs(sum(mdot.values()) - TOTAL_MDOT) < 1e-6


def test_coupling_increases_spread_vs_uniform():
    """Routing bypass flow through guide tubes widens the coolant spread
    relative to the uniform-flow baseline (the §28 mechanism)."""
    channels = build_channels(n_fuel=7, guide_positions={2, 6}, q_pin=60000.0)
    _, T_uniform, _, _, _ = solve_coupled(channels, coupled=False)
    _, T_coupled, _, _, _ = solve_coupled(channels, coupled=True)
    spread_u = max(T_uniform.values()) - min(T_uniform.values())
    spread_c = max(T_coupled.values()) - min(T_coupled.values())
    assert spread_c > spread_u


def test_guide_tubes_stay_cool():
    """Guide-tube channels carry zero power -> stay near inlet T."""
    channels = build_channels(n_fuel=7, guide_positions={2, 6}, q_pin=60000.0)
    _, T_exit, _, _, _ = solve_coupled(channels, coupled=True)
    # Guide tubes near inlet (565 K); fuel channels heated above
    assert T_exit["ch2"] < T_exit["ch0"]
    assert T_exit["ch6"] < T_exit["ch0"]
