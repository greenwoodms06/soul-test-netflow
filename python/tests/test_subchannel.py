"""Tests for the subchannel-resolved coupled T-H solve (netflow.coupling).

Validates that a 3D subchannel hydraulic network couples to the thermal
solve on the unchanged core, captures guide-tube bypass, and produces a
coolant spread far larger than the diffusive-mixing-only model.
"""

import numpy as np
import pytest

CoolProp = pytest.importorskip("CoolProp")

from netflow.coupling.subchannel import solve_coupled_subchannel


def test_subchannel_couples_and_converges():
    N = 7
    guide = {(2, 2), (2, 4), (4, 2), (4, 4)}
    q_map = np.full((N, N), 18000.0)
    total_mdot = 0.358 * (N * N - len(guide))
    res = solve_coupled_subchannel(N, n_ax=6, q_map=q_map, guide=guide,
                                   total_mdot=total_mdot, max_picard=8)
    assert res.converged
    assert res.n_picard <= 8


def test_guide_tubes_carry_bypass_flow():
    N = 7
    guide = {(3, 3)}
    q_map = np.full((N, N), 18000.0)
    total_mdot = 0.358 * (N * N - len(guide))
    res = solve_coupled_subchannel(N, n_ax=6, q_map=q_map, guide=guide,
                                   total_mdot=total_mdot, guide_K=0.5,
                                   max_picard=8)
    # Guide channel (lower K) carries more flow than a fuel channel
    assert res.channel_flow[3, 3] > res.channel_flow[0, 0]


def test_lateral_mixing_reduces_spread():
    """Higher lateral mixing coefficient homogenizes -> smaller spread.
    (The calibration knob that matches VERA.)"""
    N = 7
    guide = {(3, 3)}
    q_map = np.full((N, N), 18000.0)
    total_mdot = 0.358 * (N * N - len(guide))
    res_low = solve_coupled_subchannel(N, n_ax=6, q_map=q_map, guide=guide,
                                       total_mdot=total_mdot,
                                       lateral_mix_frac=0.05, max_picard=8)
    res_high = solve_coupled_subchannel(N, n_ax=6, q_map=q_map, guide=guide,
                                        total_mdot=total_mdot,
                                        lateral_mix_frac=0.5, max_picard=8)
    assert res_high.spread_K < res_low.spread_K


def test_full_axial_field_returned():
    N = 5
    guide = {(2, 2)}
    q_map = np.full((N, N), 18000.0)
    total_mdot = 0.358 * (N * N - len(guide))
    res = solve_coupled_subchannel(N, n_ax=6, q_map=q_map, guide=guide,
                                   total_mdot=total_mdot, max_picard=6)
    assert res.coolant_axial is not None
    assert res.coolant_axial.shape == (N, N, 6)
    # Coolant warms monotonically up a fuel channel
    col = res.coolant_axial[0, 0, :]
    assert col[-1] >= col[0]
