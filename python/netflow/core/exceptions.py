"""Public exception types raised by netflow.core."""


class NetflowError(Exception):
    """Base class for all netflow errors."""


class BadBC(NetflowError):
    """A boundary-condition specification is malformed or contradictory.

    Examples: a Dirichlet node also given a Neumann source > 0 (ambiguous);
    no Dirichlet anywhere in a connected component (problem is undefined).
    """


class DisconnectedGraph(NetflowError):
    """A connected component of interior nodes has no path to any Dirichlet.

    The system would be singular. The error carries the list of
    offending node IDs so the caller can find them.
    """

    def __init__(self, message: str, node_ids: list[str] | None = None):
        super().__init__(message)
        self.node_ids = node_ids or []


class SingularJacobian(NetflowError):
    """The assembled Jacobian was singular at Newton iteration k.

    Usually a sign of a disconnected sub-network that ``validate()``
    missed, or a degenerate edge (R = 0).
    """

    def __init__(self, message: str, iteration: int, row: int | None = None):
        super().__init__(message)
        self.iteration = iteration
        self.row = row


class NonConvergence(NetflowError):
    """The nonlinear solver did not reach ``tol`` within ``max_iter``.

    Only raised when the user passes ``raise_on_nonconverge=True`` to
    ``Network.solve_steady``. The default behavior returns a Result
    with ``converged=False`` and full residual history.
    """

    def __init__(self, message: str, residual_history, n_iter: int):
        super().__init__(message)
        self.residual_history = residual_history
        self.n_iter = n_iter
