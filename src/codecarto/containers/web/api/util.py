def generate_return(status: str, message: str, results: str):
    return {
        "status": status,  # success or error
        "message": message,  # friendly message
        "results": results,  # the actual results or the error message
    }


def web_exception(status: str, message: str, exc) -> dict:
    import traceback

    tb_str = traceback.format_exception(type(exc), exc, exc.__traceback__)
    tb_str = "".join(tb_str)
    return generate_return(
        status,
        message,
        {"e": exc, "traceback": tb_str},
    )
