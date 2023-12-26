from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager

databases: list = ["test_database", "ccdb"]
dbName: str = "test_database"


@asynccontextmanager
async def mongo_client():
    client = AsyncIOMotorClient("database", 27017)
    try:
        yield client
    finally:
        client.close()


async def destory_database():
    async with mongo_client() as client:
        # drop collection
        col_list = await client[dbName].list_collection_names()
        for col in col_list:
            await client[dbName][col].delete_many({})

        # drop database
        db_list = await client.list_database_names()

        # pop the required db, admin, config, and local
        db_list.pop(db_list.index("admin"))
        db_list.pop(db_list.index("config"))
        db_list.pop(db_list.index("local"))

        # drop the remaining databases
        for db in db_list:
            await client.drop_database(db)


# This is here as a test to see if I can get the collection to connect
def get_db_col():
    try:
        client = AsyncIOMotorClient("database", 27017)
        db = client["networkx_db"]
        collection = db["graphs"]
        yield collection
    finally:
        client.close()
