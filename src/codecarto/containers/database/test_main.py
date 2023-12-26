import pytest
import networkx as nx
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

from . import mongo as ctx


# Create the app
app = FastAPI()


######## Utility Functions ########
def create_graph():
    G = nx.DiGraph()
    G.add_node(1, label="Node A", color="red", shape="triangle")
    G.add_node(2, label="Node B", color="green", shape="octagon")
    G.add_edge(1, 2, label="Edge from A to B", color="blue")
    return G


def graph_to_dict(G: nx.Graph) -> dict:
    return {
        "nodes": [{"id": n, **d} for n, d in G.nodes(data=True)],
        "edges": [{"source": u, "target": v, **d} for u, v, d in G.edges(data=True)],
    }


######## Setup Client & Database ########
@pytest.mark.asyncio
async def setup_db():
    client = AsyncIOMotorClient("localhost", 27017)
    # client = TestClient(app)
    db = client["test_database"]
    return db


######## Initial Database Functions ########
@pytest.mark.asyncio
async def save_to_mongo(graph_data: dict):
    async with ctx.mongo_client() as client:
        db = client.ccdb
        result = await db["graphs"].insert_one(graph_data)
        return result.inserted_id


@pytest.mark.asyncio
async def fetch_from_mongo(filter):
    async with ctx.mongo_client() as client:
        db = client.ccdb
        result = await db["graphs"].find_one(filter=filter)
        return result


@pytest.mark.asyncio
async def fetch_all_from_mongo():
    async with ctx.mongo_client() as client:
        db = client.ccdb
        return [doc async for doc in db["graphs"].find()]


@pytest.mark.asyncio
async def remove_from_mongo(filter):
    async with ctx.mongo_client() as client:
        db = client.ccdb
        result = await db["graphs"].delete_one(filter=filter)
        return result


######## Test Functions ########
@pytest.mark.asyncio
async def test_setup():
    # purge the database initially to ensure a clean test
    async with ctx.mongo_client() as client:
        client.drop_database("test_database")


@pytest.mark.asyncio
async def test_db_connection():
    from pprint import pformat

    async with ctx.mongo_client() as client:
        db = await ctx.db_create("test_database")
        print(f"\n\ninit database:\n{pformat(db)}\n")
        assert db is not None


@pytest.mark.asyncio
async def test_user_collection():
    from pprint import pformat

    async with ctx.mongo_client() as client:
        db = client.ccdb
        await ctx.col_create("users")
        # get the list of collections in the database
        results = await db.list_collection_names()
        print(f"\n\ninit collections:\n{pformat(results)}\n")
        assert "users" in results


@pytest.mark.asyncio
async def test_create_user():
    from pprint import pformat

    async with ctx.mongo_client() as client:
        db = client.ccdb

        # create a user
        new_user = {
            "username": "jdoe",
            "email": "jdoe@test.com",
            "password": "johnRules1",
            "first_name": "John",
            "last_name": "Doe",
        }
        results = await ctx.user_create(**new_user)
        print(f"\n\ninserted user:\n{pformat(results)}\n")
        assert results is not None
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0] is not None
        objID = results[0]
        id = str(results[0])
        assert isinstance(id, str)

        # get the schema of the users collection
        schema = await ctx.col_schema("users")
        print(f"\n\nusers schema:\n{pformat(schema)}\n")
        assert schema is not None
        user_schema = ctx.user_schema
        assert set(schema.keys()) == set(user_schema.keys())

        # authenticate the user: True
        results = await ctx.user_auth("jdoe", "johnRules1")
        print(f"\n\nauthenticated user:\n{pformat(results)}\n")
        assert results is not None
        assert isinstance(results, bool)
        assert results is True

        # authenticate the user: False
        results = await ctx.user_auth("jdoe", "johnRules2")
        print(f"\n\nauthenticated user:\n{pformat(results)}\n")
        assert results is not None
        assert isinstance(results, bool)
        assert results is False

        # get the user
        users = await ctx.doc_select(table_name="users", filter={"_id": objID})
        print(f"\n\nselected user:\n{pformat(users)}\n")
        assert users is not None
        assert isinstance(users, list)
        assert len(users) == 1
        user = users[0]
        assert user is not None
        assert isinstance(user, dict)
        assert user.get("_id") == objID
        assert user.get("first_name") == "John"
        assert user.get("last_name") == "Doe"
        assert user.get("username") == "jdoe"
        assert user.get("email") == "jdoe@test.com"
        # assert user.get("password") == "johnRules1"
        assert user.get("created_date") is not None
        from datetime import datetime

        assert isinstance(user.get("created_date"), datetime)

        # remove the user
        results = await ctx.user_remove(user.get("username"))
        print(f"\n\nremoved user:\n{pformat(results)}\n")
        assert results is not None
        assert isinstance(results, int)
        assert results == 1

        # try to get the user again
        user = await ctx.doc_select("users", filter={"_id": objID})
        print(f"\n\nselected user:\n{pformat(user)}\n")
        assert len(user) == 0

        # add user back in for purge test
        results = await ctx.user_create(**new_user)
        print(f"\n\ninserted user again:\n{pformat(results)}\n")
        assert results is not None
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0] is not None
        objID = results[0]
        id = str(results[0])
        assert isinstance(id, str)


@pytest.mark.asyncio
async def test_purge():
    from pprint import pformat

    async with ctx.mongo_client() as client:
        # get a list of all collections
        db = client.ccdb
        col_list = await db.list_collection_names()
        print(f"\n\ncollections:\n{pformat(col_list)}\n")
        assert col_list is not None
        assert len(col_list) > 0

        for col in col_list:
            # check if there are docs in each collection
            results = await ctx.doc_count(col)
            print(f"\n\ncounted docs in '{col}':\n{pformat(results)}\n")
            assert results is not None
            assert isinstance(results, int)
            assert results > 0

            # clear all docs in collections
            results = await ctx.col_clear(col)
            print(f"\n\ncleared docs in '{col}':\n{pformat(results)}\n")
            assert results is not None
            assert isinstance(results, int)
            assert results == 1

            # check if there are docs in each collection
            results = await ctx.doc_count(col)
            print(f"\n\ncounted docs in '{col}':\n{pformat(results)}\n")
            assert results is not None
            assert isinstance(results, int)
            assert results == 0

        # drop all collections
        results = await ctx.col_drop(col_list)
        print(f"\n\ndropped collections:\n{pformat(results)}\n")
        assert results is not None
        assert isinstance(results, int)
        assert results == len(col_list)

    # purge the database
    client.drop_database("test_database")
    print(f"\n\npurged database\n")
