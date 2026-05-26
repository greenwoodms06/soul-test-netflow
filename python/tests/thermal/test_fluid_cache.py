"""Regression tests for CoolPropFluid property cache.

The cache was originally implemented with nearest-bucket quantization,
which broke Newton convergence for non-identical workloads (cf. tally
§17). The fix was bracket-and-linearly-interpolate. These tests lock
that contract in place.
"""

import math

import pytest

CoolProp = pytest.importorskip("CoolProp")

from netflow.plugins.thermal import CoolPropFluid


def test_cache_returns_same_value_for_identical_T():
    f = CoolPropFluid("Water", default_P=15.5e6, cache_T_resolution=0.05)
    a = f.k(300.0, None)
    b = f.k(300.0, None)
    assert a == b
    assert f.cache_stats()["entries"] >= 1


def test_cache_is_continuous_across_bucket_boundaries():
    """Linear interpolation between adjacent buckets must be continuous
    in T. Jumping across a bucket boundary should change k by no more
    than the local slope * bucket width."""
    f = CoolPropFluid("Water", default_P=15.5e6, cache_T_resolution=0.05)
    # Pick a bucket boundary explicitly: 0.05 * 6000 = 300.0
    eps = 1e-7
    just_below = f.k(300.0 - eps, None)
    just_above = f.k(300.0 + eps, None)
    # The interpolated function should be smooth — the jump across
    # the boundary should be far smaller than the bucket width times
    # any reasonable property slope.
    assert math.isclose(just_below, just_above, rel_tol=1e-5)


def test_cache_matches_uncached_within_quantization_tolerance():
    """Interpolated cache value at an arbitrary T should match the
    uncached PropsSI value to within ~bucket_width × |dk/dT|."""
    from CoolProp.CoolProp import PropsSI

    f_cached = CoolPropFluid("Water", default_P=15.5e6, cache_T_resolution=0.5)
    f_uncached = CoolPropFluid("Water", default_P=15.5e6, cache_T_resolution=0.0)

    T = 327.13   # not on any bucket boundary
    k_cached = f_cached.k(T, None)
    k_uncached = f_uncached.k(T, None)
    # Linear interpolation through PropsSI vs PropsSI itself: should agree
    # to roughly bucket_width²·|d²k/dT²|/2. At 0.5 K resolution we expect
    # rel error well under 1e-4.
    assert math.isclose(k_cached, k_uncached, rel_tol=1e-3)


def test_cache_disabled_with_zero_resolution():
    f = CoolPropFluid("Water", default_P=15.5e6, cache_T_resolution=0.0)
    f.k(300.0, None)
    f.k(305.0, None)
    f.k(310.0, None)
    # All three are exact buckets at res=0
    assert f.cache_stats()["entries"] == 3


def test_cache_two_buckets_per_call_when_T_off_grid():
    """When T is not exactly on a bucket boundary, the cache fills *two*
    entries (the lower and upper brackets). This is the cost of smooth
    interpolation."""
    f = CoolPropFluid("Water", default_P=15.5e6, cache_T_resolution=0.5)
    f.k(327.13, None)
    assert f.cache_stats()["entries"] == 2


def test_cache_clear():
    f = CoolPropFluid("Water", default_P=15.5e6, cache_T_resolution=0.05)
    f.k(300.0, None)
    assert f.cache_stats()["entries"] >= 1
    f.clear_cache()
    assert f.cache_stats()["entries"] == 0


def test_newton_convergence_with_cache_on_nonidentical_workload():
    """Smoke test for the §17 regression: non-identical convection states
    must not stall Newton when the cache is on."""
    import math as m
    from netflow import Network, Node
    from netflow.plugins.thermal import (
        ContactResistance,
        ForcedConvection,
    )

    water = CoolPropFluid("Water", default_P=15.5e6, cache_T_resolution=0.05)

    # Five small networks with *different* wall temperatures so cache
    # buckets straddle differently per network.
    for T_wall in (310.0, 325.0, 340.0, 360.0, 380.0):
        net = Network()
        net.add_node(Node(id="hot", fixed=T_wall))
        net.add_node(Node(id="wall"))
        net.add_node(Node(id="bulk", fixed=300.0))
        net.add_edge(ContactResistance("hot", "wall", R=0.01))
        conv = ForcedConvection(
            "wall", "bulk", fluid=water,
            mdot=0.5, D_h=0.02, A_ht=m.pi * 0.02,
            wall_side="a",
        )
        net.add_edge(conv)
        res = net.solve_steady(method="newton", tol=1e-6, max_iter=20)
        assert res.converged, (
            f"non-identical workload failed to converge at T_wall={T_wall}: "
            f"||F||={res.residual_history[-1]}"
        )
