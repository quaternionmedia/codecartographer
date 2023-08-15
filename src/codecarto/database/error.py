from ..utils.errors import (
    ThemeError,
    ThemeCreationError,
    ThemeNotFoundError,
    ThemeDirNotFoundError,
    CliError,
    ThemeBaseNotFoundError,
    MissingParameterError,
)


class ErrorHandler:
    def __init__(self):
        self.error_handler = None

        # Parent types
        self.CliError = CliError
        self.ThemeError = ThemeError

        # Children types
        self.MissingParameterError = MissingParameterError
        self.ThemeBaseNotFoundError = ThemeBaseNotFoundError
        self.ThemeCreationError = ThemeCreationError
        self.ThemeDirNotFoundError = ThemeDirNotFoundError
        self.ThemeNotFoundError = ThemeNotFoundError

    def log(
        self,
        exception: Exception = None,
        caller: str = None,
        break_line: int = -1,
        message: str = None,
    ) -> None:
        """Logs an exception.

        Parameters:
        -----------
            exception (Exception):
                The exception to log.
            caller (str):
                The caller of the exception.
            break_line (int):
                The line code broke at.
            message (str):
                The message to log.
        """

        # TODO: Move this to an Error sub module
        # Log the error in error.log and record in ErrorLog table in database
        # TODO: need to format error.log write input
        pass

    def raise_error(self, error: str, exception: Exception = None) -> None:
        """Raises an error.

        Parameters:
        -----------
            error (str):
                The error message to raise.
            exception (Exception):
                The exception to raise.
        """

        # TODO: Adapt this to be codecarto custom instead of just random raised error
        # need the type of ERROR to be general and not just ValueError or whatever

        if exception:
            # Raise exception if provided
            raise exception
        else:
            # Raise ValueError if no exception provided
            # This is in cases where not wrapped in try/catch
            raise ValueError(error)
