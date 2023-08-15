# TODO: go through errors in package and make sure they're custom and not just generic exceptions.
# ^^^ IF NEEDED


class CliError(Exception):
    """Base class for CLI-related errors."""

    pass


class MissingParameterError(CliError):
    """Raised when a new command requires all parameters."""

    pass


class ThemeError(Exception):
    """Base class for exceptions in the Theme module."""

    pass


class ThemeBaseNotFoundError(ThemeError):
    """Raised when the specified base theme is not found."""

    pass


class ThemeCreationError(ThemeError):
    """Raised when a new theme could not be created."""

    pass


class ThemeDirNotFoundError(CliError):
    """Raised when themes.json cannot be found."""

    pass


class ThemeNotFoundError(ThemeError):
    """Raised when the specified theme is not found."""

    pass
