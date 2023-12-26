import pytest

from .connection import mongo_client, dbName
from .exceptions import DBSyntaxError


import logging

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def doc_insert(table_name: str, data: list[dict] | dict) -> list[str]:
    """Insert records(docs) into a table(collection).

    Parameters
    ----------
    table_name : str
        The name of the table(collection).
    data : list[dict] | dict
        The data to insert.

    Returns
    -------
    list[str]
        The ids of the inserted records(docs).
    """
    # Validate the inputs
    data_list: list = None
    if not table_name or table_name == "":
        raise DBSyntaxError("Insert function requires a table name.")
    if not data or data == [] or data == {}:
        raise DBSyntaxError(
            "Insert function requires a list[dict] or dict of data to insert."
        )
    elif isinstance(data, dict):
        data_list = [data]

    # Connect to the database
    async with mongo_client() as client:
        # Insert the data and return the ids
        result = await client[dbName][table_name].insert_many(data_list)
        return result.inserted_ids


@pytest.mark.asyncio
async def doc_select(
    table_name: str,
    num_recs: int = None,
    distinct: bool = False,
    distinct_key: str = None,
    filter: dict = None,
    filter_key: str = None,
    filter_value: str = None,
) -> dict:
    """Select a records(docs) from a table(collection) where a filter is applied.

    Parameters
    ----------
    table_name : str
        The name of the table(collection).
    num_recs : int = None
        The number of records to return.
    distinct : bool = False
        If true, retrieve distinct values for the provided distinct_key.
    distinct_key : str = None
        The field for which to retrieve distinct values. Required if distinct is True.
    filter: dict = None
        The filter to apply.
    filter_key : str = None
        The key to filter on.
    filter_value : str = None
        The value to filter on. Can be another dict for more complex filters.
            ex: {'field': {'$gt': 'value'}}
        - $gt, $gte, $lt, $lte, $ne, $in, $nin, $exists, $regex, $elemMatch

    Returns
    -------
    dict
        The record(doc) selected.
    """
    # Validate the inputs
    if not table_name or table_name == "":
        raise DBSyntaxError("Select function requires a table name.")
    if distinct and (not distinct_key or distinct_key == ""):
        raise DBSyntaxError(
            "Select function requires a distinct key if distinct is True"
        )

    # Construct the filter
    if filter is None:
        if filter_key and filter_value:
            filter = {filter_key: {"$gt": filter_value}}
        else:
            filter = {}

    # Connect to the database
    async with mongo_client() as client:
        collection = client[dbName][table_name]

        # Handle distinct, if requested, and return the results
        if distinct:
            return await collection.distinct(distinct_key, filter)

        # Apply the filter
        if num_recs is not None:
            cursor = collection.find(filter).limit(num_recs)
        else:
            cursor = collection.find(filter)

        # Limit the number of results
        results = await cursor.to_list(
            length=num_recs if num_recs is not None else None
        )

        # Return the results
        return results


@pytest.mark.asyncio
async def doc_update(
    table_name: str,
    data: dict,
    filter: dict = None,
    filter_key: str = None,
    filter_value: str = None,
) -> int:
    """Update records(docs) in a table(collection).

    Parameters
    ----------
    table_name : str
        The name of the table(collection).
    data : dict
        The data to update.
    filter: dict, optional
        The filter to apply.
    filter_key : str, optional
        The key to filter on.
    filter_value : str, optional
        The value to filter on.

    Returns
    -------
    int
        The number of records(docs) updated.
    """
    # Construct the filter
    if (filter is None or filter == {}) and (
        (filter_key is None or filter_key == "")
        or (filter_value is None or filter_value == "")
    ):
        raise DBSyntaxError("Remove function requires at least one filter.")

    if filter is None and filter_key and filter_value:
        filter = {filter_key: filter_value}

    if not filter:
        raise DBSyntaxError("Update function requires an id or a valid filter.")

    async with mongo_client() as client:
        # Update the data and return the number of records updated
        from pprint import pformat

        print(f"\ndocuemnt.py - doc_update() - data:\n{pformat(data)}")
        result = await client[dbName][table_name].update_many(filter, {"$set": data})
        return result.modified_count


@pytest.mark.asyncio
async def doc_remove(
    table_name: str,
    filter: dict = None,
    filter_key: str = None,
    filter_value: str = None,
) -> int:
    """Remove records(doc) from a table(collection).

    Parameters
    ----------
    table_name : str
        The name of the table(collection).
    filter: dict = None
        The filter to apply.
    filter_key : str = None
        The key to filter on.
    filter_value : str = None
        The value to filter on. Can be another dict for more complex filters.
            ex: {'field': {'$gt': 'value'}}
        - $gt, $gte, $lt, $lte, $ne, $in, $nin, $exists, $regex, $elemMatch

    Returns
    -------
    int
        The number of records(docs) deleted.
    """
    # Validate the inputs
    if (not table_name or table_name == "") and id is None:
        raise DBSyntaxError(
            "Remove function requires either a table name or a table id."
        )
    if (filter is None or filter == {}) and (
        (filter_key is None or filter_key == "")
        or (filter_value is None or filter_value == "")
    ):
        raise DBSyntaxError("Remove function requires at least one filter.")

    # Connect to the database
    async with mongo_client() as client:
        # Construct the filter for multiple deletions
        if filter is None and filter_key and filter_value:
            filter = {filter_key: filter_value}

        # WARNING: do not delete all records if no filter is provided
        # Return the results
        result = await client[dbName][table_name].delete_many(filter)
        return result.deleted_count


@pytest.mark.asyncio
async def doc_clear_field(table_name: str, field_name: str) -> int:
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
    # TODO: does this clear the field in dict? or does it remove it?

    # Validate the inputs
    if not table_name or table_name == "":
        raise DBSyntaxError("Drop function requires a table name.")
    if not field_name or field_name == "":
        raise DBSyntaxError("Drop function requires a field name.")

    # Connect to the database
    async with mongo_client() as client:
        results = await client[dbName][table_name].update_many(
            {}, {"$unset": {field_name: ""}}
        )
        return results.modified_count


@pytest.mark.asyncio
async def doc_count(table_name: str, filter: dict = None):
    """Count the number of documents in a table(collection).

    Parameters
    ----------
    table_name : str
        The name of the table(collection).
    filter: dict = None
        The filter to apply.

    Returns
    -------
    int
        The number of records(docs) in the table(collection).
    """
    # Validate the inputs
    if not table_name or table_name == "":
        raise DBSyntaxError("Count function requires a table name.")

    # Connect to the database
    async with mongo_client() as client:
        count = await client[dbName][table_name].count_documents(
            filter if filter else {}
        )
        return count
