"""TEST - UTILS
Misc helpers/utils functions for tests
"""

# # Native # #
from datetime import datetime
from random import randint

# # Project # #
from ..models.user import *
from ..repos.user_repo import *
from ..util import get_uuid

__all__ = ("get_user_create", "get_existing_user", "get_uuid")


def get_user_create(**kwargs):
    return UserCreate(
        **{
            "user_id": get_uuid(),
            **kwargs,
        }
    )


def get_existing_user(**kwargs):
    return UserRepo.create(get_user_create(**kwargs))
