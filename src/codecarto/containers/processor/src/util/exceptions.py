class GithubError(Exception):
    """General GitHub error"""

    def __init__(
        self,
        source: str,
        params: dict,
        message: str = "GitHub API returned 500",
        status_code: int = 500,
        exc: Exception = None,
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
        exc: Exception = None,
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
        exc: Exception = None,
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
        exc: Exception = None,
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
        exc: Exception = None,
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
        exc: Exception = None,
    ):
        super().__init__(source, params, message, status_code, exc)
