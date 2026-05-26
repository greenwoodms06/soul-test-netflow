"""netflow.core — generic graph + sparse assembly + nonlinear solver.

This module must not import from netflow.plugins or any domain library
(CoolProp, IAPWS, etc.). The layering test in tests/test_layering.py
enforces this at CI time.
"""

from netflow.core.node import Node
from netflow.core.edge import Edge
from netflow.core.network import Network
from netflow.core.result import Result
from netflow.core import exceptions

__all__ = ["Node", "Edge", "Network", "Result", "exceptions"]
