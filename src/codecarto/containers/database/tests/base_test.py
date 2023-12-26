from motor.motor_asyncio import AsyncIOMotorClient

from ..models.user import *
from ..actions import *
from ..actions.util import hash_password
from ..actions.collection import col_clear, col_drop


__all__ = ("BaseTest",)


class BaseTest:
    """Base class for tests."""
