# # Native # #
from datetime import date
from typing import Optional
from contextlib import suppress

# # Installed # #
import pydantic
from pydantic import Field

# # Package # #
from .common import BaseModel
from ..util import get_time, get_uuid

__all__ = (
    "UserFields",
    "UserUpdate",
    "UserCreate",
    "UserRead",
    "UsersRead",
)

_string = dict(min_length=1)
"""Common attributes for all String fields"""
_unix_ts = dict(example=get_time())
"""Common attributes for all Unix timestamp fields"""


"""
MODELS - FIELDS
Definition of Fields used on model classes attributes.
We define them separately because the UserUpdate and UserCreate models need to re-define their attributes,
as they change from Optional to required.
Address could define its fields on the model itself, but we define them here for convenience
"""


class UserFields:
    username = Field(
        description="Username used to login", example="JSmith123", **_string
    )
    password = Field(
        description="Password used to login", example="JSmithRules1", **_string
    )
    user_id = Field(
        description="Unique identifier of this user in the database",
        example=get_uuid(),
        min_length=36,
        max_length=36,
    )
    """The user_id is the _id field of Mongo documents, and is set on UserRepo.create"""

    created = Field(
        alias="created",
        description="When the user was registered (Unix timestamp)",
        **_unix_ts,
    )
    """Created is set on UserRepo.create"""

    updated = Field(
        alias="updated",
        description="When the user was updated for the last time (Unix timestamp)",
        **_unix_ts,
    )
    """Created is set on UserRepo.update (and initially on create)"""


"""
MODELS - USER - UPDATE
User Update model. All attributes are set as Optional, as we use the PATCH method for update
(in which only the attributes to change are sent on request body)
"""


class UserUpdate(BaseModel):
    """Body of User PATCH requests"""

    username: Optional[str] = UserFields.username
    password: Optional[str] = UserFields.password
    updated: Optional[date] = UserFields.updated

    def dict(self, **kwargs):
        # The "updated" field must be converted to string
        # (isoformat) when exporting to dict (for Mongo)
        d = super().dict(**kwargs)
        with suppress(KeyError):
            d["updaed"] = d.pop("updated").isoformat()
        return d


"""
MODELS - USER - CREATE
User Create model. Inherits from UserUpdate, but all the required fields must be re-defined
"""


class UserCreate(UserUpdate):
    """Body of User POST requests"""

    username: str = UserFields.username
    password: str = UserFields.password
    create: date = UserFields.created


"""
MODELS - USER - READ
User Read model. Inherits from UserCreate and adds the user_id field, which is the _id field on Mongo documents
"""


class UserRead(UserCreate):
    """Body of User GET and POST responses"""

    user_id: str = UserFields.user_id
    created: int = UserFields.created
    updated: int = UserFields.updated

    @pydantic.root_validator(pre=True)
    def _set_user_id(cls, data):
        """Swap the field _id to user_id (this could be done with field alias, by setting the field as "_id"
        and the alias as "user_id", but can be quite confusing)"""
        document_id = data.get("_id")
        if document_id:
            data["user_id"] = document_id
        return data

    @pydantic.root_validator()
    def _set_password(cls, data):
        """Sw"""
        pw = data.get("password")
        if pw:
            data["password"] = pw  # encrypt this
        return data

    class Config(UserCreate.Config):
        extra = (
            pydantic.Extra.ignore
        )  # if a read document has extra fields, ignore them


UsersRead = list[UserRead]
