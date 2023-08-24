from fastapi import APIRouter, UploadFile, HTTPException, File
from fastapi.responses import JSONResponse

from ...parser.parser import Parser
from ...polygraph.polygraph import PolyGraph

# Create a router and add the limiter to it
ParserRoute: APIRouter = APIRouter()


@ParserRoute.get(
    "/parse",
    response_class=JSONResponse,
    responses={200: {"content": {"application/json": {}}}},
)
async def parse(
    source_files: list[UploadFile] = File(...), language: str = "Python"
) -> dict[str, str]:
    """Parses source code.

    Parameters:
    -----
        source_files (list[UploadFile]):
            The list of source files.
        language (str):
            The language of the source code.
            CURRENTLY ONLY PYTHON IS SUPPORTED.

    Returns:
    --------
        JSONResponse:
            The json data representing the graph of source code.
    """

    # Check if source files were provided
    if not source_files:
        raise ValueError(
            caller="API/parser/parse",
            break_line=28,
            msg="HTTP Status:400 - No source files provided.",
        )
    else:
        # TODO: add support for other languages Parser.parse_source_files(source_files, language)
        try:
            # Validate file sizes and type, done here instead of wrapper to avoid passing large files
            passed_files: list[UploadFile] = source_files.copy()
            for file in source_files:
                # Check file sizes
                if (
                    file.file._file.tell() > 1000000
                ):  # Limit file size to 1MB for this example
                    msg: str = f"HTTP Status:413 - File size for {file.filename} exceeds the limit of 1MB."
                    raise HTTPException(status_code=413, detail=msg)
                # Check file type is supported
                supported_file_types = [".py"]
                if file.filename[-3:] not in supported_file_types:
                    # Remove the file from the list of files to be parsed
                    passed_files.remove(file)

            # Check if there are any files left to parse
            if not passed_files or len(passed_files) == 0:
                msg: str = f"HTTP Status:415 - No supported file types provided."
                raise HTTPException(status_code=415, detail=msg)

            # Parse the source code and return the {json_data, output_dir} dict
            parser: Parser = Parser()
            polygraph: PolyGraph = PolyGraph()
            graph = parser.parse_list([file.file for file in passed_files])
            json_data = polygraph.graph_to_json_data(graph)

            # Return the json data
            return JSONResponse(
                content=json_data
            )  # Serializes the content to a JSON string.
        except Exception as e:
            # internal server error log
            raise HTTPException(status_code=500, detail=str(e))
