from fastapi import APIRouter

from api.util import generate_return, proc_exception, proc_error

# DEBUG
import logging

logger = logging.getLogger(__name__)

# Create a router
PolyGraphRoute = APIRouter()


@PolyGraphRoute.get("/get_graph_desc")
async def get_graph_desc() -> dict:
    """Get the graph description.

    Returns:
        dict: Graph description
    """
    try:
        logger.info(f"  Started     Proc.get_graph_desc()")
        from src.database.graph_data import get_graph_description

        graph_desc: dict = get_graph_description()

        return generate_return(
            200,
            "Graph description successfully fetched from processor.",
            graph_desc,
        )
    except Exception as e:
        proc_exception(
            "get_graph_desc",
            "Could not fetch graph description",
            {},
            e,
        )
    finally:
        logger.info(f"  Finished    Proc.get_graph_desc()")


@PolyGraphRoute.get("/url_to_json")
async def url_data_to_json(file_url: str) -> dict:
    """Convert a URL data to JSON.

    Parameters:
        file_url (str): URL to convert

    Returns:
        dict: JSON data
    """
    try:
        logger.info(f"  Started     Proc.url_data_to_json(): file_url - {file_url}")
        from src.polygraph.polygraph import graph_to_json_data
        from src.parser.import_source_url import read_data_from_url
        from src.parser.parser import Parser

        url_data = await read_data_from_url(file_url)
        filename = file_url.split("/")[-1]
        if isinstance(url_data, dict):
            url_data = str(url_data)
        parser: Parser = Parser(None, {"raw": url_data, "filename": filename})
        graph = parser.graph

        json_data = graph_to_json_data(graph)
        return generate_return(200, "Proc - Success", json_data)
    except Exception as exc:
        proc_exception(
            "url_data_to_json",
            "Error when converting raw data to JSON",
            {"file_url": file_url},
            exc,
        )
    finally:
        logger.info(f"  Finished    Proc.url_data_to_json()")
