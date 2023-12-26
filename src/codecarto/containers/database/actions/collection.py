import pytest

from .connection import mongo_client, dbName
from .exceptions import DBSyntaxError


@pytest.mark.asyncio
async def col_create(table_name: str, data: list[dict] | dict = None) -> int:
    """Create a table(collection) in the database.

    Parameters
    ----------
    table_name : str
        The name of the table(collection).
    data :  list[dict] | dict, optional
        The data to insert into the table(collection).

    Returns
    -------
    int
        The number of tables(collections) created.
    """
    # Validate the inputs
    if not table_name or table_name == "":
        raise DBSyntaxError("Create function requires a table name.")

    # Connect to the database
    async with mongo_client() as client:
        # Check if the table(collection) exists
        col_list = await client[dbName].list_collection_names()
        if table_name in col_list:
            return 0
        else:
            # Create the table(collection) and return the number of tables created
            result = await client[dbName].create_collection(table_name)

            # Insert the data into the table(collection) if it exists
            if data:
                if isinstance(data, dict):
                    await client[dbName][table_name].insert_one(data)
                else:
                    await client[dbName][table_name].insert_many(data)

            return result


@pytest.mark.asyncio
async def col_get_id(table_name: str) -> str:
    """Return the id of a table(collection) in the database.

    Parameters
    ----------
    table_name : str
        The name of the table(collection).

    Returns
    -------
    str
        The table(collection) id selected
    """
    # Validate the inputs
    if not table_name or table_name == "":
        raise DBSyntaxError("Select function requires a table name.")

    # Connect to the database
    async with mongo_client() as client:
        # Check if the table(collection) exists
        col_list = await client[dbName].list_collection_names()
        if table_name not in col_list:
            return None
        else:
            # Return the table(collection) id
            return client[dbName][table_name].id


@pytest.mark.asyncio
async def col_rename(table_name: str, new_name: str) -> int:
    """Rename a table(collection) in the database.

    Parameters
    ----------
    table_name : str
        The name of the table(collection).
    new_name : str
        The new name of the table(collection).

    Returns
    -------
    int
        The number of tables(collections) renamed.
    """
    # Validate the inputs
    if not table_name or table_name == "":
        raise DBSyntaxError("Rename function requires a table name.")
    if not new_name or new_name == "":
        raise DBSyntaxError("Rename function requires a new table name.")

    # Connect to the database
    async with mongo_client() as client:
        await client[dbName][table_name].rename(new_name)


@pytest.mark.asyncio
async def col_alter(table_name: str, field_name: str, default_value=None) -> int:
    """Add a new field to all records(docs) in a table(collection).

    Parameters
    ----------
    table_name : str
        The name of the table(collection).
    field_name : str
        The name of the field to alter.
    default_value : any, optional
        The default value to set for the field.

    Returns
    -------
    int
        The number of records(docs) altered.
    """
    # Validate the inputs
    if not table_name or table_name == "":
        raise DBSyntaxError("Alter function requires a table name.")
    if not field_name or field_name == "":
        raise DBSyntaxError("Alter function requires a field name.")

    # Connect to the database
    async with mongo_client() as client:
        results = await client[dbName][table_name].update_many(
            {}, {"$set": {field_name: default_value}}
        )
        return results.modified_count


@pytest.mark.asyncio
async def col_drop(table_name: str | list[str]) -> int:
    """Drop a table(collection) from the database.

    Parameters
    ----------
    table_name : str
        The name of the table(collection).

    Returns
    -------
    int
        The number of tables(collections) dropped.
    """
    # Validate the inputs
    if (
        not table_name
        or table_name == ""
        or (isinstance(table_name, list) and len(table_name) == 0)
    ):
        raise DBSyntaxError("Drop function requires a table name.")

    # Connect to the database
    async with mongo_client() as client:
        # Check if the table(collection) is list
        deleted_count = 0
        if isinstance(table_name, list):
            for col in table_name:
                # Check if the table(collection) exists
                col_list = await client[dbName].list_collection_names()
                if col not in col_list:
                    continue
                await client[dbName][col].drop()
                deleted_count += 1
        else:
            await client[dbName][table_name].drop()
            deleted_count += 1

        # Return the number of tables(collections) dropped
        return deleted_count


async def col_clear(table_name: str) -> int:
    """Clear a table(collection) of all records(docs).

    Parameters
    ----------
    table_name : str
        The name of the table(collection).

    Returns
    -------
    int
        The number of records(docs) removed from the table(collection).
    """
    # Validate the inputs
    if not table_name or table_name == "":
        raise DBSyntaxError("Clear function requires a table name.")

    # Connect to the database
    async with mongo_client() as client:
        # Clear the table(collection) and return the number of records removed
        result = await client[dbName][table_name].delete_many({})
        num_deleted = result.deleted_count
        return num_deleted


async def col_drop_field(table_name: str, field_name: str) -> dict:
    """Drop a field from all records(docs) in a table(collection).

    Parameters
    ----------
    table_name : str
        The name of the table(collection).
    field_name : str
        The name of the field to drop.

    Returns
    -------
    int
        The number of records(docs) altered.
    """

    # Validate the inputs
    if not table_name or table_name == "":
        raise DBSyntaxError("Drop function requires a table name.")
    if not field_name or field_name == "":
        raise DBSyntaxError("Drop function requires a field name.")

    # TODO: does this remove the field from dict? or just set it to None?
    # Connect to the database
    async with mongo_client() as client:
        results = await client[dbName][table_name].update_many(
            {}, {"$unset": {field_name: ""}}
        )
        return results.modified_count


async def col_schema(table_name: str) -> dict:
    """Return the schema of a table(collection).

    Parameters
    ----------
    table_name : str
        The name of the table(collection).

    Returns
    -------
    dict
        The schema of the table(collection).
    """
    # Validate the inputs
    if not table_name or table_name == "":
        raise DBSyntaxError("Schema function requires a table name.")

    # Connect to the database
    async with mongo_client() as client:
        # Fetch a single document from the collection
        doc = await client[dbName][table_name].find_one()

        if doc is None:
            return {}

        # Extract the keys and their types from the document
        schema = {key: type(value).__name__ for key, value in doc.items()}

        return schema
