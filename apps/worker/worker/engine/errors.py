"""Engine error hierarchy."""


class EngineError(Exception):
    """Base class for recoverable engine errors that mark a run as failed."""


class WorkflowLoadError(EngineError):
    """The workflow version could not be loaded."""


class GraphValidationError(EngineError):
    """The workflow graph failed validation."""


class MaxStepsExceededError(EngineError):
    """The run exceeded its maximum allowed steps."""


class MaxRuntimeExceededError(EngineError):
    """The run exceeded its maximum allowed runtime."""


class InvalidJobError(Exception):
    """A Redis job payload was malformed (handled outside the run lifecycle)."""
