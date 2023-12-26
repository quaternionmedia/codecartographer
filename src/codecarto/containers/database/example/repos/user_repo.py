"""REPOSITORIES
Methods to interact with the database
"""

# # Package # #
from ..models.user import *
from ..exceptions import *
from ..connection import db
from ..util import get_time, get_uuid

__all__ = ("UserRepo",)


class UserRepo:
    @staticmethod
    def get(user_id: str) -> UserRead:
        """Retrieve a single User by its unique id"""
        document = db.find_one({"_id": user_id})
        if not document:
            raise UserNotFoundException(user_id)
        return UserRead(**document)

    @staticmethod
    def list() -> UsersRead:
        """Retrieve all the available users"""
        cursor = db.find()
        return [UserRead(**document) for document in cursor]

    @staticmethod
    def create(create: UserRead) -> UserRead:
        """Create a user and return its Read object"""
        document = create.dict()
        document["created"] = document["updated"] = get_time()
        document["_id"] = get_uuid()
        # The time and id could be inserted as a model's Field default factory,
        # but would require having another model for Repository only to implement it

        result = db.insert_one(document)
        assert result.acknowledged

        return UserRead.get(result.inserted_id)

    @staticmethod
    def update(user_id: str, update: UserUpdate):
        """Update a user by giving only the fields to update"""
        document = update.dict()
        document["updated"] = get_time()

        result = db.update_one({"_id": user_id}, {"$set": document})
        if not result.modified_count:
            raise UserNotFoundException(identifier=user_id)

    @staticmethod
    def delete(user_id: str):
        """Delete a user given its unique id"""
        result = db.delete_one({"_id": user_id})
        if not result.deleted_count:
            raise UserNotFoundException(identifier=user_id)
