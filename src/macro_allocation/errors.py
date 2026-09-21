"""Expected failures that should be shown without a traceback."""


class ProjectError(Exception):
    """Base class for safe, user-facing project failures."""


class ConfigurationError(ProjectError):
    """The declared strategy configuration is invalid or unresolved."""


class DataValidationError(ProjectError):
    """Real input data is missing, ambiguous, or unsuitable."""


class ReproductionIncomplete(ProjectError):
    """The backtest cannot be completed without changing the strategy."""

