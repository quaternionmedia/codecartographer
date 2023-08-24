from fastapi import APIRouter
from ...processor import process

ProcessorRoute = APIRouter()


@ProcessorRoute.get("/process")
async def process(
    file_path: str = __file__, single_file: bool = False
) -> dict[str, str]:
    """Runs the code cartographer.

    Parameters:
    -----------
    file_path (str) - Default: __file__
        The path to the file to be analyzed.
    single_file (bool) - Default: False
        Whether to analyze a single file.

    Returns:
    --------
    dict:
        The json_data of the processed source code.
    """
    return process(
        file_path=file_path,
        api=True,
        single_file=single_file,
    )
