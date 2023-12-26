from motor import MotorChangeStream

from .connection import mongo_client
from .exceptions import DBSyntaxError


async def db_create(db_name: str):
    """Create a database.

    Parameters
    ----------
    db_name : str
        The name of the database.

    Returns
    -------
    database
        The created database.
    """
    # Validate the inputs
    if not db_name or db_name == "":
        raise DBSyntaxError("Create function requires a database name.")

    # Connect to the database
    async with mongo_client() as client:
        # Create the database and return the database
        result = client[db_name]
        return result


async def db_watch(db_name: str) -> MotorChangeStream:
    """Watch a database.

    Parameters
    ----------
    db_name : str
        The name of the database.

    Returns
    -------
    MotorChangeStream
        The database stream.
    """
    # Validate the inputs
    if not db_name or db_name == "":
        raise DBSyntaxError("Watch function requires a database name.")

    # Connect to the database
    async with mongo_client() as client:
        # Watch the database and return the database
        result = await client[db_name].watch()
        return result


async def db_rename(db_name: str, new_name: str):
    """Rename a database.

    Parameters
    ----------
    db_name : str
        The name of the database.
    new_name : str
        The new name of the database.

    Returns
    -------
    int
        The number of databases renamed.
    """
    # Validate the inputs
    if not db_name or db_name == "":
        raise DBSyntaxError("Rename function requires a database name.")
    if not new_name or new_name == "":
        raise DBSyntaxError("Rename function requires a new database name.")

    # Connect to the database
    async with mongo_client() as client:
        await client[db_name].rename(new_name)


async def db_drop(db_name: str) -> int:
    """Drop a database.

    Parameters
    ----------
    db_name : str
        The name of the database.

    Returns
    -------
    int
        The number of databases dropped.
    """
    # Validate the inputs
    if not db_name or db_name == "":
        raise DBSyntaxError("Drop function requires a database name.")

    # Connect to the database
    async with mongo_client() as client:
        # Drop the database and return the number of databases dropped
        result = await client.drop_database(db_name)
        return result
