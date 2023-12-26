"""TEST READ
Test read actions (get one, list)
"""

# # Package # #
from .base import BaseTest
from .util import *


class TestGet(BaseTest):
    def test_get_existing_user(self):
        """Having an existing user, get it.
        Should return the user"""
        user = get_existing_user()

        response = self.get_user(user.user_id)
        assert response.json() == user.dict()

    def test_get_nonexisting_user(self):
        """Get a user that does not exist.
        Should return not found 404 error and the identifier"""
        user_id = get_uuid()

        response = self.get_user(user_id)
        assert response.json()["identifier"] == user_id


class TestList(BaseTest):
    def test_list_users(self):
        """Having multiple users, list all of them.
        Should return all of them in array"""
        users = [get_existing_user() for _ in range(4)]

        response = self.list_users()
        assert response.json() == [u.dict() for u in users]
