"""Tests for cosine_axial_shape — preserves average, peak at midpoint."""

import math

import pytest

from netflow.bench.fuel_array import cosine_axial_shape


def test_peak_at_midpoint():
    s = cosine_axial_shape(peak_factor=1.5)
    assert math.isclose(s(0.5), 1.5, rel_tol=1e-9)


def test_minimum_at_ends():
    s = cosine_axial_shape(peak_factor=1.5)
    # 2 - peak_factor = 0.5
    assert math.isclose(s(0.0), 0.5, rel_tol=1e-9)
    assert math.isclose(s(1.0), 0.5, rel_tol=1e-9)


def test_average_is_unity():
    """Integral of shape over [0, 1] equals 1 (preserves assembly average)."""
    s = cosine_axial_shape(peak_factor=1.6)
    # Numerical integration via fine grid
    N = 10_000
    avg = sum(s((i + 0.5) / N) for i in range(N)) / N
    assert math.isclose(avg, 1.0, abs_tol=1e-5)


def test_peak_factor_bounds():
    with pytest.raises(ValueError, match="peak_factor"):
        cosine_axial_shape(0.5)
    with pytest.raises(ValueError, match="peak_factor"):
        cosine_axial_shape(2.5)


def test_uniform_at_peak_factor_one():
    """peak_factor=1 must give a constant shape equal to 1."""
    s = cosine_axial_shape(peak_factor=1.0)
    for z in (0.0, 0.25, 0.5, 0.75, 1.0):
        assert math.isclose(s(z), 1.0, rel_tol=1e-9)


def test_attribute_for_inspection():
    s = cosine_axial_shape(peak_factor=1.4)
    assert s.peak_factor == 1.4
