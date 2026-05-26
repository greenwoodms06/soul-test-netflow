"""Tests for the fixed_point outer-loop driver."""

import math

import numpy as np

from netflow.core.iterate import fixed_point


def test_scalar_fixed_point_sqrt():
    """Babylonian sqrt as a fixed point: x -> (x + a/x)/2 converges to √a."""
    a = 2.0
    res = fixed_point(lambda x: 0.5 * (x + a / x), np.array([1.0]), tol=1e-12)
    assert res.converged
    assert math.isclose(float(res.state[0]), math.sqrt(a), rel_tol=1e-10)


def test_vector_fixed_point_contraction():
    """A linear contraction x -> 0.5 x + b converges to the fixed point 2b."""
    b = np.array([1.0, -2.0, 3.0])
    res = fixed_point(lambda x: 0.5 * x + b, np.zeros(3), tol=1e-12)
    assert res.converged
    assert np.allclose(res.state, 2 * b, atol=1e-9)


def test_nonconvergence_reported():
    """A divergent map should report not-converged within max_iter."""
    res = fixed_point(lambda x: 2.0 * x + 1.0, np.array([1.0]),
                      tol=1e-9, max_iter=5)
    assert not res.converged
    assert res.n_iter == 5


def test_history_recorded():
    res = fixed_point(lambda x: 0.5 * x, np.array([1.0]), tol=1e-6)
    assert len(res.history) == res.n_iter
    # deltas should be monotonically shrinking for this contraction
    assert all(a >= b for a, b in zip(res.history, res.history[1:]))


def test_under_relaxation():
    """Relaxation should still reach the same fixed point (more slowly)."""
    b = np.array([4.0])
    res = fixed_point(lambda x: 0.5 * x + b, np.zeros(1), tol=1e-10,
                      relax=0.5)
    assert res.converged
    assert math.isclose(float(res.state[0]), 8.0, rel_tol=1e-7)
