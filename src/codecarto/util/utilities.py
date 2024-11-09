import logging
from pprint import pprint

logger = logging.getLogger()


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

    @staticmethod
    def warning(message: str):
        logger.warning(message)

    @staticmethod
    def critical(message: str):
        logger.critical(message)

    @staticmethod
    def pprint(message: object):
        pprint(message)


def generate_return(
    status: int = 200, message: str = "Success", results: str | dict | list = {}
):
    return {
        "status": status,
        "message": message,
        "results": results,
    }
