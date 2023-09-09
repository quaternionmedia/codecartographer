def generate_return(status: str, message: str, results: str):
    return {
        "status": status,  # success or error
        "message": message,  # friendly message
        "results": results,  # the actual results or the error message
    }


def web_exception(
    called_from: str,
    message: str,
    params: dict = {},
    exc: Exception = None,
    status: int = 500,
    proc_error: str = "",
) -> dict:
    import traceback
    import logging
    from fastapi import HTTPException

    # log the error and stack trace
    error_message = f"Web.{called_from}() - status: {status} - param: {params} - message: {message} - proc_error: {proc_error}"
    logger = logging.getLogger(__name__)
    logger.error(error_message)
    if exc:
        error_message = f"{error_message} - exception: {str(exc)}"
        tbk_str = traceback.format_exception(type(exc), exc, exc.__traceback__)
        tbk_str = "".join(tbk_str)
        logger.error(tbk_str)

    # raise the exception
    raise HTTPException(
        status_code=500,
        detail=error_message,
    )
