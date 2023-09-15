import logging

logger = logging.getLogger(__name__)


def generate_return(status: int = 200, message: str = "", results: str = {}):
    return {
        "status": status,
        "message": message,
        "results": results,
    }


def proc_error(
    called_from: str,
    message: str,
    params: dict = {},
    status: int = 500,
    proc_error: str = "",
):
    """Return error results when something is wrong in processor container but did not throw exception"""
    # Generate msg based on proc error status
    msg: str = ""
    if status != 500:
        if status == 403:
            msg = "Github API - Forbidden"
        elif status == 404:
            msg = "URL Not Found"
    else:
        msg = {message}

    error_message = f"\n\n\tWeb.{called_from}() \n\tstatus: {status} \n\tmessage: {msg} \n\tparam: {params} \n\tproc_error: {proc_error}"
    logger.error(f"{error_message}\n")

    # return the error
    return generate_return(
        status=status,
        message=msg,
        results={"proc_error": proc_error},
    )


def web_exception(
    called_from: str,
    message: str,
    params: dict = {},
    exc: Exception = None,
    status: int = 500,
) -> dict:
    """Raise an exception if there is an error with the web container"""
    import traceback
    from fastapi import HTTPException

    # log the error and stack trace
    error_message = f"\n\n\Web.{called_from}() \n\tstatus: {status} message: {message} \n\tparam: {params}\n"
    logger.error(error_message)

    # create a stack trace
    if exc:
        error_message = f"\Web.exception: {str(exc)} \n\tmessage:{error_message}\n"
        tbk_str = traceback.format_exception(type(exc), exc, exc.__traceback__)
        tbk_str = "".join(tbk_str)
        logger.error(f"\n\t{tbk_str}")

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
