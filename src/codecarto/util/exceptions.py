from typing import Optional

import httpx
from util.utilities import Log, generate_return


def proc_error(called_from: str, message: str, params: dict = {}, status: int = 500):
    """Return error results when something is wrong but did not throw exception"""
    # Generate msg based on proc error status
    error_message = f"\n\n\tProc.{called_from}() \n\tstatus: {status} \n\tmessage: {message} \n\tparam: {params} \n"
    Log.error(f"{error_message}")

    # return the error
    return generate_return(status=status, message=message, results=params)


def proc_exception(
    called_from: str,
    message: str,
    params: dict = {},
    exc: Optional[Exception] = None,
    status: int = 500,
):
    """Raise an exception if there is an exception thrown in processor"""
    import traceback
    from fastapi import HTTPException

    # log the error and stack trace
    error_message = f"\n\n\tProc.{called_from}() \n\tstatus: {status} message: {message} \n\tparam: {params}\n"
    Log.error(error_message)

    # create a stack trace
    if exc:
        error_message = f"\tProc.exception: {str(exc)} \n\tmessage:{error_message}\n"
        tbk_str = traceback.format_exception(type(exc), exc, exc.__traceback__)
        tbk_str = "".join(tbk_str)
        Log.error(f"\n\t{tbk_str}")

    # raise the exception
    if status != 500:
        raise HTTPException(
            status_code=status,
            detail=error_message,
        )
    else:
        raise HTTPException(
            status_code=500,
            detail=error_message,
        )


class NotebookError(Exception):
    """Base class for notebook exceptions."""

    def __init__(self, source, params, message):
        self.source = source
        self.params = params
        self.message = message


class ImportSourceUrlError(Exception):
    """Import Source Url error"""

    def __init__(
        self,
        source: str,
        params: dict,
        message: str = "Import Source Url error",
        status_code: int = 500,
        exc: Exception | None = None,
    ):
        self.source = source
        self.message = message
        self.status_code = status_code
        self.params = params
        self.exc = exc


class ImportSourceUrlHttpError(httpx.RequestError):
    """Import Source Url Httpx error"""

    def __init__(
        self,
        source: str,
        params: dict,
        message: str = "Import Source Url Httpx error",
        status_code: int = 500,
        exc: Exception | None = None,
    ):
        super().__init__(message)
        self.source = source
        self.params = params
        self.status_code = status_code
        self.exc = exc


class PolyGraphError(Exception):
    """Base class for exceptions in this module."""

    def __init__(self, source, params, message):
        self.source = source
        self.params = params
        self.message = message


class GravisDBError(Exception):
    """Base class for gravis database exceptions."""

    def __init__(self, source, params, message):
        self.source = source
        self.params = params
        self.message = message


class GravisDBHttpError(GravisDBError):
    """Base class for gravis database http exceptions."""

    def __init__(self, source, params, message, status_code):
        super().__init__(source, params, message)
        self.status_code = status_code


class GithubError(Exception):
    """General GitHub error"""

    def __init__(
        self,
        source: str,
        params: dict,
        message: str = "GitHub API returned 500",
        status_code: int = 500,
        exc: Exception | None = None,
    ):
        self.source = source
        self.params = params
        self.message = message
        self.status_code = status_code
        self.exc = exc


class GithubAPIError(GithubError):
    """GitHub API key not found"""

    def __init__(
        self,
        source: str,
        params: dict,
        message: str = "GitHub API key not found",
        status_code: int = 403,
        exc: Exception | None = None,
    ):
        super().__init__(source, params, message, status_code, exc)


class GithubSizeError(GithubError):
    """GitHub repo is too large"""

    def __init__(
        self,
        source: str,
        params: dict,
        message: str = "GitHub repo is too large",
        status_code: int = 500,
        exc: Exception | None = None,
    ):
        super().__init__(source, params, message, status_code, exc)


class GithubNoDataError(GithubError):
    """No data returned from GitHub API for URL"""

    def __init__(
        self,
        source: str,
        params: dict,
        message: str = "No data returned from GitHub API for URL",
        status_code: int = 404,
        exc: Exception | None = None,
    ):
        super().__init__(source, params, message, status_code, exc)


class Github403Error(GithubError):
    """GitHub API returned 403"""

    def __init__(
        self,
        source: str,
        params: dict,
        message: str = "GitHub API returned 403",
        status_code: int = 403,
        exc: Exception | None = None,
    ):
        super().__init__(source, params, message, status_code, exc)


class Github404Error(GithubError):
    """GitHub API returned 404"""

    def __init__(
        self,
        source: str,
        params: dict,
        message: str = "GitHub API returned 404",
        status_code: int = 404,
        exc: Exception | None = None,
    ):
        super().__init__(source, params, message, status_code, exc)
