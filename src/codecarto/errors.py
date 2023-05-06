class ThemeError(Exception):
    """Base class for exceptions in the Theme module."""

    pass


class ThemeNotFoundError(ThemeError):
    """Raised when the specified theme is not found."""

    pass


class BaseNotFoundError(ThemeError):
    """Raised when the specified base theme is not found."""

    pass


class ThemeCreationError(ThemeError):
    """Raised when a new theme could not be created."""

    pass


class CliError(Exception):
    """Base class for CLI-related errors."""

    pass


class ThemesDirNotFoundError(CliError):
    """Raised when themes.json cannot be found."""

    pass


class MissingParameterError(CliError):
    """Raised when a new command requires all parameters."""

    pass
