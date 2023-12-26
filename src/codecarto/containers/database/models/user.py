import bcrypt
from datetime import datetime
from bson import ObjectId

from ..actions.document import *
from ..actions.collection import *
from ..models.base import *

# collections are dictionaries with a name and schema
# docs are dictionaries with values to the collection schema

# create users collection
user_schema = {  # it will create an ID by default
    "_id": "ObjectID",  # mongo given id, not required
    # "first_name": "string",  # encrypt this
    # "last_name": "string",  # encrypt this
    "username": "string",  # encrypt this
    # "email": "string",  # encrypt this
    "password": "string",  # encrypt this
    "created_date": "datetime",  # user profile created at timestamp
    "updated_date": "datetime",  # user profile updated at timestamp
    # "last_login_date": "datetime",  # user last login timestamp
    # "user_status_id": "string",  # user status id, corresponds to a user_status collection of user statuses
    # "custom_palettes": "list",  # list of custom palette ids?? should this be a list of docs instead? Cause these are specific to the user
    # "current_palette_id": "int",  # id of current palette
    # "site_settings": "collection",  # collection of site settings, including theme
    # "repo_history": "list",  # list of repo urls sorted by most recent
}
# TODO: so we use 'name' for the collection name,
# and 'schema' for the list of fields and their types in the collection
# then docs (key"field": value"field_value") are added to the collection


class User(BaseModel):
    username: str
    password: str
    created_date: datetime
    updated_date: datetime


class UserCollection(BaseCollection):
    name: str
    users: list[User]


UserCol: UserCollection = UserCollection()
UserCol.name = "users"
UserCol.users = []


def create_random_user() -> dict:
    """Create a random user.

    Returns
    -------
    dict:
        a random set of user data
    """
    import random
    import string
    from ..actions.util import hash_password

    # dynamically create a random username
    username = "".join(random.choices(string.ascii_letters, k=10))
    password = hash_password("".join(random.choices(string.ascii_letters, k=10)))

    data = {
        "username": username,
        "password": password,
    }
    return data


async def user_create(
    username: str,
    password: str,
) -> User | None:
    """Create a new user.

    Parameters
    ----------
    username: str
        username of the user to create
    password: str
        password of the user to create

    Returns
    -------
    User:
        the user created
    """
    # Validate the inputs
    if not username or not isinstance(username, str) or len(username) == 0:
        return None
    if not password or not isinstance(password, str) or len(password) == 0:
        return None

    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    create_time = datetime.now()

    # Create the user data
    user_data = {
        "username": username,
        "password": hashed_password.decode("utf-8"),
        "created_date": create_time,
        "updated_date": create_time,
        # ... other fields with their default or provided values
    }

    # Insert the user data into the DB
    user_ids = await doc_insert(UserCol.name, user_data)

    # Create the user object
    user: User = User()
    user.id = user_ids[0]
    user.username = username
    user.password = hashed_password
    user.created_date = create_time
    user.updated_date = create_time

    # Add the user object to the collection object
    UserCol.users.append(user)

    # Return the user object
    return user


async def user_auth(
    user_id: str,
    password: str,
) -> bool:
    """Authenticate a user.

    Parameters
    ----------
    user_id: str
        id of the user to authenticate

    Returns
    -------
    bool:
        if user was authorized
    """
    # Validate the inputs
    if not user_id or not isinstance(user_id, str) or user_id == "":
        return False
    if not password or not isinstance(password, str) or len(password) == 0:
        return False

    # Retrieve the user from the DB
    user: User = user_select(user_id)
    if not user:
        return False

    # Check the password
    hashed_password = (
        user[0].get("password").encode("utf-8")
    )  # Assuming the user data is the first entry in the list
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password)


async def user_remove(user_id: str) -> int:
    """Remove a user.

    Parameters
    ----------
    user_id: str
        id of the user to remove

    Returns
    -------
    int:
        number of users deleted
    """
    # Validate the inputs
    if not user_id or not isinstance(user_id, str) or user_id == "":
        return -1

    # Remove the user
    removed_count: int = await doc_remove(
        UserCol.name, filter={"_id": ObjectId(user_id)}
    )

    # Remove the user from the collection object
    if removed_count > 0:
        for user in UserCol.users:
            if user.id == user_id:
                UserCol.users.remove(user)
                break

    # Return the number of users removed
    return removed_count


async def user_select(user_id: str = None) -> list[User] | None:
    """Select a user.

    Parameters
    ----------
    user_id: strt
        id of the user to select

    Returns
    -------
    list[User]:
        the users selected, even if only one
    """
    # Get the user from user id
    if user_id is None:
        _user: User = await doc_select(UserCol.name)
    else:
        # Validate the inputs
        if not user_id or not isinstance(user_id, str) or user_id == "":
            return None
        _user: User = await doc_select(UserCol.name, filter={"_id": ObjectId(user_id)})

    if not _user or len(_user) == 0:
        return None

    # Create/Get the user object(s)
    users = []
    if isinstance(_user, list):
        for user in _user:
            # Check if the user is in the UserCol object
            found = False
            for u in UserCol.users:
                if u.id == user["_id"]:
                    users.append(u)
                    found = True
                    break
            if found:
                continue

            # If not, create the user object
            u: User = User()
            u.id = user["_id"]
            u.username = user["username"]
            u.password = user["password"]
            u.created_date = user["created_date"]
            u.updated_date = user["updated_date"]
            users.append(u)
    else:
        # Check if the user is in the UserCol object
        found = False
        for u in UserCol.users:
            if u.id == _user["_id"]:
                users.append(u)
                found = True
                break

        if found:
            # If not, create the user object
            user: User = User()
            user.id = _user["_id"]
            user.username = _user["username"]
            user.password = _user["password"]
            user.created_date = _user["created_date"]
            user.updated_date = _user["updated_date"]
            users.append(user)

    # Return the user object(s)
    return users


async def user_update(user_id: int, new_data: dict) -> int:
    """Update a user.

    Parameters
    ----------
    user_id: int
        id of the user to update
    new_data: dict
        dictionary of fields to update

    Returns
    -------
    int:
        number of users updated
    """
    # Validate the inputs
    if not user_id or not isinstance(user_id, str) or user_id == "":
        return -1
    if not new_data or not isinstance(new_data, dict) or len(new_data) == 0:
        return -2

    # Check if the new_data has any extra fields
    for field in new_data.keys():
        if field not in user_schema.keys():
            # Remove the extra field
            new_data.pop(field)

    # Get the user
    users: list = await user_select(user_id)
    if not users or len(users) == 0:
        return -3
    user: User = users[0]
    if not user:
        return -4

    # Make sure the updated data has all the required fields
    # If not, create them with default values
    update_data = new_data
    update_data["updated_date"] = datetime.now()
    for field in user_schema.keys():
        if field not in update_data.keys():
            if field == "_id":
                update_data[field] = user.id
            elif field == "created_date":
                update_data[field] = user.created_date
            elif field == "username":
                update_data[field] = user.username
            elif field == "password":
                update_data[field] = user.password

    # Update the user in the database
    updated: int = await doc_update(
        UserCol.name,
        data=update_data,
        filter={"_id": ObjectId(user_id)},
    )

    # Update the user in the collection object
    if updated > 0:
        for u in UserCol.users:
            if u.id == user_id:
                u.username = update_data["username"]
                u.password = update_data["password"]
                u.created_date = update_data["created_date"]
                u.updated_date = update_data["updated_date"]
                break
    return updated
