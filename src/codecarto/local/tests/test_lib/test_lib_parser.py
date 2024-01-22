import tempfile
from pathlib import Path

from ...src.codecarto import Parser


def test_parser():
    """Test Parser class functions and output graph."""
    try:
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Get the source files of 'test_source_code' directory
            source_files = list(Path("tests/test_source_code").rglob("*.py"))

            # Create a Parser object
            parser: Parser = Parser(source_files)

            # get back parser's graph
            graph = parser.graph

            # check nodes in the graph
            assert len(graph.nodes) > 0
            assert len(graph.nodes) == 9
            assert graph.number_of_nodes() == 9

            # get the ids of nodes in the graph
            node_ids = [node_id for node_id in graph.nodes]

            # check if the ids are unique
            assert len(node_ids) == len(set(node_ids))

            # check if the ids are in the range of the number of nodes
            assert all(
                node_id in range(graph.number_of_nodes()) for node_id in node_ids
            )

            # check some parameters around graph.nodes

    except Exception as e:
        # Raise exception
        raise e
