import pytest
from datetime import datetime

from ..models.user import (
    User,
    create_random_user,
    user_create,
    user_auth,
    user_remove,
    user_schema,
    user_select,
    user_update,
    UserCol,
)
from ..actions.util import random_id
from ..actions.connection import mongo_client, destory_database, dbName


@pytest.mark.asyncio
async def test_setup():
    # purge the database initially to ensure a clean test
    await destory_database()

    # create main database
    async with mongo_client() as client:
        assert client is not None
        db_list = await client.list_database_names()
        print(f"\n\nsetup_function: db_list: {db_list}")
        assert db_list is not None
        assert len(db_list) == 3

        client.drop_database(dbName)
        db = client[dbName]
        await db.create_collection(UserCol.name)


class TestUserCreate:
    @pytest.mark.asyncio
    async def test_create_user(self):
        data: dict = create_random_user()
        user: User = await user_create(data["username"], data["password"])
        print(f"\n\ncreate user: user.id: {user.id}")
        assert user is not None
        assert user.username == data["username"]

    @pytest.mark.asyncio
    async def test_create_user_without_username(self):
        print(f"\n\ncreate user no username:")
        user: User = await user_create(username=None, password="pass123")
        assert user is None

    @pytest.mark.asyncio
    async def test_timestamp_created_updated(self):
        expected_timestamp = datetime.now()

        data: dict = create_random_user()
        user: User = await user_create(data["username"], data["password"])
        print(f"\n\ntimestamp created updated: user.id: {user.id}")
        assert user is not None
        assert user.created_date == user.updated_date
        assert user.created_date == expected_timestamp


class TestUserDelete:
    @pytest.mark.asyncio
    async def test_delete_user(self):
        # check there is only one user
        users: list = await user_select()
        print(f"\n\ndelete existing: len(users): {len(users)}")
        assert len(users) > 0

        # delete the users
        if isinstance(users, list):
            user: User = users[0]
        else:
            user: User = users
        print(f"\n\ndelete existing: user.id: {str(user.id)}")

        deleted_count: int = await user_remove(str(user.id))
        assert deleted_count == 1

        # check there is only one user left
        remaining_users: list = await user_select()
        assert isinstance(remaining_users, list)
        assert len(remaining_users) == 1

    @pytest.mark.asyncio
    async def test_delete_nonexisting_user(self):
        user_id = random_id()
        print(f"\n\ndelete nonexisting: user_id: {str(user_id)}")
        non_existing: int = await user_remove(str(user_id))
        assert non_existing == 0


class TestUserUpdate:
    @pytest.mark.asyncio
    async def test_update_user_single_attribute(self):
        users: list = await user_select()
        user: User = users[0]
        print(f"\n\nupdate single: len(users): {len(users)}")
        print(f"update single: user.id: {str(user.id)}")
        print(f"update single: user.username: {user.username}")
        print(f"update single: user.password: {user.password}")
        print(f"update single: user.created_date: {user.created_date}")
        print(f"update single: user.updated_date: {user.updated_date}")
        rand_user: User = create_random_user()
        new_name = rand_user["username"]
        print(f"update single: new_name: {new_name}")
        user_data = {
            "username": new_name,
            "password": user.password,
            "created_date": user.created_date,
            "updated_date": user.updated_date,
        }
        updated = await user_update(str(user.id), user_data)
        assert updated is not None
        assert updated == 1
        assert user.username != new_name

    @pytest.mark.asyncio
    async def test_update_nonexisting_user(self):
        users: list = await user_select()
        user: User = users[0]
        rand_user: User = create_random_user()
        new_name = rand_user["username"]
        rand_id = random_id()
        user_data = {
            "username": new_name,
            "password": user.password,
            "created_date": user.created_date,
            "updated_date": user.updated_date,
        }
        updated = await user_update(rand_id, user_data)
        assert updated is None

    @pytest.mark.asyncio
    async def test_update_user_none_attributes(self):
        users: list = await user_select()
        user: User = users[0]
        updated = await user_update(str(user.id), {})
        assert updated is None

    @pytest.mark.asyncio
    async def test_update_user_extra_attributes(self):
        users: list = await user_select()
        user: User = users[0]
        user_data = {
            "username": user.username,
            "password": user.password,
            "created_date": user.created_date,
            "updated_date": user.updated_date,
            "foo": "bar",
        }
        updated = await user_update(str(user.id), user_data)
        assert updated is not None
        assert updated == 1
        assert user["foo"] is None

    @pytest.mark.asyncio
    async def test_timestamp_updated(self):
        expected_timestamp = datetime.now()

        users: list = await user_select()
        user: User = users[0]
        random_user = create_random_user()
        user_data = {
            "username": user.username,
            "password": random_user["password"],
        }
        updated = await user_update(str(user.id), user_data)
        assert updated is not None
        assert updated == 1
        assert user.updated_date == expected_timestamp
        assert user.created_date == user.created_date


@pytest.mark.asyncio
async def test_teardown():
    await destory_database()
    users: list = await user_select()
    assert users is None
