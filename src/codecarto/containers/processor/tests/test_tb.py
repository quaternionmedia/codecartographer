import pytest
from pprint import pprint
from graphbase.src.main import (
    insert_graph,
    read_graph,
    client,
)

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Example JSON graph (replace with your actual test data)
test_graph_name = "my_graph_name"
test_json_graph = {
    "name": test_graph_name,
    "nodes": [{"id": "1", "label": "Node 1"}, {"id": "2", "label": "Node 2"}],
    "links": [{"source": "1", "target": "2"}],
}


def test_setup():
    # check database
    logger.debug(f"\nDatabases:")
    logger.debug(f"\n{client.list_database_names()}\n")
    assert "graphbase" in client.list_database_names()

    # clear the collection
    client["graphbase"]["graph"].delete_many({})
    logger.debug(f"Cleared graph Collection:")
    logger.debug(f"\n{client['graphbase']['graph'].find()}\n")
    assert client["graphbase"]["graph"].find_one() == None


def test_connection():
    db_list = client.list_database_names()
    assert db_list is not None
    assert "graphbase" in db_list


@pytest.mark.asyncio
async def test_insert():
    results = await insert_graph(name=test_graph_name, graph_data=test_json_graph)
    assert results is not None
    assert results["message"] == "Graph created successfully"


@pytest.mark.asyncio
async def test_read():
    graph = await read_graph(name=test_graph_name)
    logger.debug(f"\n\n{pprint(graph)}\n\n")
    logger.debug(f"\n\n{pprint(graph['nodes'])}\n\n")
    logger.debug(f"\n\n{pprint(graph['name'])}\n\n")
    assert graph is not None
    assert graph["name"] == test_graph_name
