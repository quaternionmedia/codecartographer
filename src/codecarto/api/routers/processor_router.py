from fastapi import APIRouter
from ...processor import Processor

router = APIRouter()


@router.get("/processor/process")
async def process(
    file_path: str = __file__, do_single_file: bool = False
) -> dict[str, str]:
    """Runs the code cartographer.

    Parameters:
    -----------
    file_path (str) - Default: __file__
        The path to the file to be analyzed.
    do_single_file (bool) - Default: False
        Whether to analyze a single file.

    Returns:
    --------
    dict:
        The json_data of the processed source code.
    """
    return Processor.process(
        file_path=file_path,
        api=True,
        do_single_file=do_single_file,
    )
