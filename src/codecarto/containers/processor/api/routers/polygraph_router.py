import httpx
from fastapi import APIRouter

from api.util import generate_return, proc_exception, proc_error

# DEBUG
import logging

logger = logging.getLogger(__name__)

# Create a router
PolyGraphRoute = APIRouter()


@PolyGraphRoute.get("/get_graph_desc")
async def get_graph_desc() -> dict:
    try:
        logger.info(f"  Started     Proc.get_graph_desc()")
        from src.models.graph_data import get_graph_description
 
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
async def url_to_json(file_url: str) -> dict:
    try:
        logger.info(f"  Started     Proc.url_to_json(): file_url - {file_url}")
        from .parser_router import raw_to_graph

        raw_data = await read_raw_data_from_url(file_url)
        filename = file_url.split("/")[-1]
        if isinstance(raw_data, dict):
            raw_data = str(raw_data)
        graph = raw_to_graph(raw_data, filename)
        json_data = graph_to_json(graph)
        return generate_return(200, "Proc - Success", json_data)
    except Exception as exc:
        proc_exception(
            "url_to_json",
            "Error when converting raw data to JSON",
            {"file_url": file_url},
            exc,
        )
    finally:
        logger.info(f"  Finished    Proc.url_to_json()")


async def read_raw_data_from_url(url: str) -> str | dict:
    try:
        logger.info(f"  Started   Proc.read_raw_data_from_url(): url - {url}")
        if not url.endswith(".py"):
            return proc_error(
                "read_raw_data_from_url",
                "URL is not a valid Python file",
                {"url": url},
                404,
            )
        client = httpx.AsyncClient() 
        response = await client.get(url) 
        if response.status_code == 200:  
            return response.text
        else:
            return proc_error(
                "read_raw_data_from_url",
                "Could not read raw data from URL",
                {"url": url},
                404,
            )
    except Exception as exc:
        proc_exception(
            "read_raw_data_from_url",
            "Error when reading raw data from URL",
            {"url": url},
            exc,
        )
    finally:
        if client:
            await client.aclose()
        logger.info(f"  Finished    Proc.read_raw_data_from_url()") 


def graph_to_json(raw_graph) -> dict:
    try:
        logger.info(f"  Started     Proc.graph_to_json() ")
        from src.polygraph.polygraph import PolyGraph

        polygraph = PolyGraph()
        json_data = polygraph.graph_to_json_data(raw_graph)
        return json_data
    except Exception as exc:
        proc_exception(
            "graph_to_json",
            "Error when transforming raw data to JSON",
            {"raw_graph": raw_graph},
            exc,
        )
    finally:
        logger.info(f"  Finished    Proc.graph_to_json()")
        

def graph_to_graphbase(digraph) -> dict:
    if not digraph:
        return proc_error(
            "digraph_to_graphbase",
            "No digraph provided",
            {"digraph": digraph},
            404,
        )
    try:
        logger.info(f"  Started     Proc.graph_to_graphbase() ")
        from src.polygraph.polygraph import PolyGraph

        polygraph = PolyGraph()
        json_data = polygraph.digraph_to_graphbase(digraph)
        return json_data
    except Exception as exc:
        proc_exception(
            "graph_to_graphbase",
            "Error when transforming graph to graph_to_graphbase",
            {"digraph": digraph},
            exc,
        )
    finally:
        logger.info(f"  Finished    Proc.graph_to_graphbase()")        
        
