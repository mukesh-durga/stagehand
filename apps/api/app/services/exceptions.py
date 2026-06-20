"""Domain exceptions for the service layer."""


class GraphValidationError(ValueError):
    """Raised when a workflow graph fails semantic validation (-> HTTP 400)."""


class WorkflowNotFoundError(Exception):
    """Raised when a workflow cannot be found (-> HTTP 404)."""


class RunNotFoundError(Exception):
    """Raised when a run cannot be found (-> HTTP 404)."""


class WorkflowNotReadyError(Exception):
    """Raised when a workflow has no current version to run (-> HTTP 409)."""


class RunNotEvaluatableError(Exception):
    """Raised when a run is not in a state that can be evaluated (-> HTTP 409)."""


class UnknownEvalTypeError(Exception):
    """Raised when an unknown eval type is requested (-> HTTP 400)."""
