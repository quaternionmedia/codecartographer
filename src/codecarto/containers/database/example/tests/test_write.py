"""TEST WRITE
Test write actions (create, update, delete)
"""

# # Native # #
from datetime import datetime
from random import randint

# # Project # #
from ..models.user import *
from ..repos.user_repo import UserRepo

# # Installed # #
import pydantic
from dateutil.relativedelta import relativedelta

# # Package # #
from .base import BaseTest
from .util import *


class UserAsCreate(UserCreate):
    """This model is used to convert UserRead to UserCreate,
    to compare the responses returned by the API with the create objects sent"""

    class Config(UserCreate.Config):
        extra = pydantic.Extra.ignore


class TestCreate(BaseTest):
    def test_create_user(self):
        """Create a user.
        Should return the user"""
        create = get_user_create().dict()

        response = self.create_user(create)
        response_as_create = UserAsCreate(**response.json())
        assert response_as_create.dict() == create

    def test_create_user_assert_birth_age(self):
        """Create a user.
        Should create the user with the given date of birth and calculate its age"""
        expected_age = randint(5, 25)
        today = datetime.now().date()
        birth = today - relativedelta(years=expected_age)
        create = get_user_create(birth=birth).dict()

        response = self.create_user(create)
        response_as_read = UserRead(**response.json())

        assert response_as_read.birth == birth
        assert response_as_read.age == expected_age

    def test_create_user_without_birth(self):
        """Create a user without date of birth.
        Should return the user without birth nor age"""
        create = get_user_create(birth=None).dict()

        response = self.create_user(create)
        response_as_read = UserRead(**response.json())

        assert response_as_read.username is None
        assert response_as_read.password is None

    def test_timestamp_created_updated(self):
        """Create a user and assert the created and updated timestamp fields.
        The creation is performed against the UserRepo,
        since mocking the time would not work as the testing API runs on another process
        """
        iso_timestamp = "2020-01-01T00:00:00+00:00"
        expected_timestamp = int(datetime.fromisoformat(iso_timestamp).timestamp())

        create = get_user_create()
        result = UserRepo.create(create)

        assert result.created == result.updated
        assert result.created == expected_timestamp


class TestDelete(BaseTest):
    def test_delete_user(self):
        """Delete a user.
        Then get it. Should end returning 404 not found"""
        user = get_existing_user()

        self.delete_user(user.user_id)
        self.get_user(user.user_id)

    def test_delete_nonexisting_user(self):
        """Delete a user that does not exist.
        Should return not found 404 error and the identifier"""
        user_id = get_uuid()

        response = self.delete_user(user_id)
        assert response.json()["identifier"] == user_id


class TestUpdate(BaseTest):
    def test_update_user_single_attribute(self):
        """Update the name of a user.
        Then get it. Should return the user with its name updated"""
        user = get_existing_user()

        new_name = get_uuid()
        update = UserUpdate(name=new_name)
        self.update_user(user.user_id, update.dict())

        read = UserRead(**self.get_user(user.user_id).json())
        assert read.name == new_name
        assert read.dict() == {
            **user.dict(),
            "name": new_name,
            "updated": read.updated,
        }

    def test_update_nonexisting_user(self):
        """Update the name of a user that does not exist.
        Should return not found 404 error and the identifier"""
        user_id = get_uuid()
        update = UserUpdate(name=get_uuid())

        response = self.update_user(user_id, update.dict())
        assert response.json()["identifier"] == user_id

    def test_update_user_none_attributes(self):
        """Update a user sending an empty object.
        Should return validation error 422"""
        user = get_existing_user()
        self.update_user(user.user_id, {})

    def test_update_user_extra_attributes(self):
        """Update a user sending unknown attributes.
        Should return validation error 422"""
        user = get_existing_user()
        self.update_user(user.user_id, {"foo": "bar"})

    def test_timestamp_updated(self):
        """Update a user and assert the updated timestamp.
        The update is performed against the UserRepo,
        since mocking the time would not work as the testing API runs on another process
        """
        iso_timestamp = "2020-04-01T00:00:00+00:00"
        expected_timestamp = int(datetime.fromisoformat(iso_timestamp).timestamp())
        user = get_existing_user()

        update = UserUpdate(name=get_uuid())
        UserRepo.update(user_id=user.user_id, update=update)

        read_response = self.get_user(user.user_id)
        read = UserRead(**read_response.json())

        assert read.updated == expected_timestamp
        assert read.updated != read.created
        assert read.created == user.created
