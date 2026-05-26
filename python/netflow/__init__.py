"""netflow — generic sparse nonlinear network solver.

Core public surface:

    from netflow import Node, Edge, Network, Result
    from netflow.exceptions import (
        SingularJacobian, DisconnectedGraph, NonConvergence, BadBC,
    )

Plugins (e.g., ``netflow.thermal``) sit atop the same public protocol an
external plugin author would use. The core has zero domain imports.
"""

from netflow.core.node import Node
from netflow.core.edge import Edge
from netflow.core.network import Network
from netflow.core.result import Result
from netflow.core import exceptions

__all__ = ["Node", "Edge", "Network", "Result", "exceptions"]
__version__ = "0.1.0.dev0"
