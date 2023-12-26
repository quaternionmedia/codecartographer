import random
import string

from .base_test import BaseTest
from ..models.user import *
from ..actions import *
from ..actions.util import hash_password


__all__ = ("BaseUserTest",)


class BaseUserTest(BaseTest):
    """Base class for user tests."""

    def create_random_user(self) -> dict:
        """Create a random user.

        Returns
        -------
        dict:
            a random set of user data
        """
        # dynamically create a random username
        username = "".join(random.choices(string.ascii_letters, k=10))
        password = hash_password("".join(random.choices(string.ascii_letters, k=10)))

        data = {
            "username": username,
            "password": password,
        }
        return data

    async def get_user(self, user_id: str) -> User:
        """Get a user from given identifier.

        Parameters
        ----------
        user_id: str
            identifier of the user to get

        Returns
        -------
        User:
            the user with given identifier
        """
        return await user_select(user_id=user_id)

    async def list_users(self) -> list[User]:
        """Get all users in database.

        Returns
        -------
        list[User]:
            all users in the database
        """
        return await user_select()

    async def create_user(self, data: dict) -> User:
        """Create a user from given date.

        Parameters
        ----------
        data: dict
            data to create the user

        Returns
        -------
        User:
            the user created
        """
        username = data.get("username")
        password = data.get("password")
        user = await user_create(username=username, password=password)
        if not user:
            return None
        return user

    async def update_user(self, user_id: str, data: dict) -> User:
        """Update a user with given data.

        Parameters
        ----------
        user_id: str
            identifier of the user to update
        data: dict
            data to update the user

        Returns
        -------
        User:
            the user created
        """
        updated_count = await user_update(user_id=user_id, update=data)
        if updated_count == 0:
            return 0
        return await self.get_user(user_id=user_id)

    async def delete_user(self, user: str | User) -> int:
        """Delete a user from given identifier.

        Parameters
        ----------
        user: str | User
            identifier of the user to delete

        Returns
        -------
        int:
            number of users deleted
        """
        # Validate the inputs
        if isinstance(user, User):
            user_id: str = user.id
        elif isinstance(user, str):
            user_id: str = user
        elif user is None:
            return -1
        else:
            return -2

        print(f"base_user.py - delete_user() - user_id: {user_id}")

        # Delete the user
        delete_count: int = await user_remove(user_id=user_id)
        return delete_count
