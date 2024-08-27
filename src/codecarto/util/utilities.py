import logging

logger = logging.getLogger(__name__)


class Log:
    @staticmethod
    def info(message: str):
        logger.info(message)

    @staticmethod
    def debug(message: str):
        logger.debug(message)

    @staticmethod
    def error(message: str):
        logger.error(message)


def generate_return(
    status: int = 200, message: str = "", results: str | dict | list = {}
):
    return {
        "status": status,
        "message": message,
        "results": results,
    }
