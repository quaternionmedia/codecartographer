import os
import pytest
import itertools
from run_helper import run_test


@pytest.mark.parametrize(
    "labels,grid,show,json",
    [args for args in itertools.product([False, True], repeat=4)],
)
def test_empty(labels, grid, show, json):
    """Test the run command with an empty file."""
    # define the path to the empty file in the tests\test_run directory
    empty_file_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "tests", "empty.py"
    )
    run_test(False, labels, grid, show, json, empty_file_path)
