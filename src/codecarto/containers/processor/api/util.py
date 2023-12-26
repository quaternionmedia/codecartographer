from typing import Optional
import logging

logger = logging.getLogger(__name__)


def generate_return(status: int = 200, message: str = "", results: str | dict = {}):
    return {
        "status": status,
        "message": message,
        "results": results,
    }


def proc_error(called_from: str, message: str, params: dict = {}, status: int = 500):
    """Return error results when something is wrong but did not throw exception"""
    # Generate msg based on proc error status
    error_message = f"\n\n\tProc.{called_from}() \n\tstatus: {status} \n\tmessage: {message} \n\tparam: {params} \n"
    logger.error(f"{error_message}")

    # return the error
    return generate_return(status=status, message=message, results=params)


def proc_exception(
    called_from: str,
    message: str,
    params: dict = {},
    exc: Optional[Exception] = None,
    status: int = 500,
) -> dict:
    """Raise an exception if there is an exception thrown in processor"""
    import traceback
    from fastapi import HTTPException

    # log the error and stack trace
    error_message = f"\n\n\tProc.{called_from}() \n\tstatus: {status} message: {message} \n\tparam: {params}\n"
    logger.error(error_message)

    # create a stack trace
    if exc:
        error_message = f"\tProc.exception: {str(exc)} \n\tmessage:{error_message}\n"
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
