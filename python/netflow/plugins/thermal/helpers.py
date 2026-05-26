"""Thermal post-processing helpers.

Currently:
* ``lmtd`` — log-mean temperature difference for a HX described by a
  ``UAEdge`` and four port temperatures.
* ``effectiveness_ntu`` — ε-NTU for parallel/counterflow HX sizing.

These are *helpers*, not network edges. Lumped resistance networks
cannot natively represent a counterflow HX (which has axial flow
gradients); they can represent a HX *as* a UA between two effective
temperatures, and these helpers extract LMTD or ε-NTU from a network
solve.
"""

from __future__ import annotations

import math


def lmtd(Th_in: float, Th_out: float, Tc_in: float, Tc_out: float) -> float:
    """Log-mean temperature difference for a counterflow HX.

    Parameters
    ----------
    Th_in, Th_out :
        Hot-stream inlet and outlet temperatures (K).
    Tc_in, Tc_out :
        Cold-stream inlet and outlet temperatures (K).

    Notes
    -----
    For counterflow:
        ΔT1 = Th_in − Tc_out,  ΔT2 = Th_out − Tc_in.
    When ΔT1 ≈ ΔT2 the formula reduces to the arithmetic mean.
    """
    d1 = Th_in - Tc_out
    d2 = Th_out - Tc_in
    if d1 <= 0 or d2 <= 0:
        raise ValueError(
            f"non-physical temperature differences: ΔT1={d1}, ΔT2={d2}"
        )
    if math.isclose(d1, d2, rel_tol=1e-6):
        return 0.5 * (d1 + d2)
    return (d1 - d2) / math.log(d1 / d2)


def effectiveness_ntu(
    NTU: float, Cr: float, flow: str = "counterflow"
) -> float:
    """ε(NTU, Cr) for the named flow arrangement.

    Parameters
    ----------
    NTU :
        Number of transfer units, UA / C_min.
    Cr :
        Capacity ratio C_min / C_max ∈ [0, 1].
    flow :
        One of ``"counterflow"``, ``"parallel"``, ``"crossflow_unmixed"``.

    Returns
    -------
    Effectiveness ε ∈ [0, 1].
    """
    if NTU < 0:
        raise ValueError("NTU must be non-negative")
    if not 0 <= Cr <= 1:
        raise ValueError("Cr must be in [0, 1]")

    if Cr == 0:
        return 1 - math.exp(-NTU)

    if flow == "counterflow":
        if Cr == 1:
            return NTU / (1 + NTU)
        num = 1 - math.exp(-NTU * (1 - Cr))
        den = 1 - Cr * math.exp(-NTU * (1 - Cr))
        return num / den
    if flow == "parallel":
        return (1 - math.exp(-NTU * (1 + Cr))) / (1 + Cr)
    if flow == "crossflow_unmixed":
        # Bowman et al. approximation
        return 1 - math.exp(
            (1 / Cr) * (NTU ** 0.22) * (math.exp(-Cr * NTU ** 0.78) - 1)
        )
    raise ValueError(f"unknown flow arrangement: {flow!r}")
