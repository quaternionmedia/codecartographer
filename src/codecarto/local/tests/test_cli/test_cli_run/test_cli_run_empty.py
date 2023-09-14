import os
import pytest
import itertools
from cli_run_helper import run_test


@pytest.mark.parametrize(
    "labels,grid,json",
    [args for args in itertools.product([False, True], repeat=3)],
)
def test_empty(labels, grid, json):
    """Test the run command with an empty file."""
    # define the path to the empty file in the same directory as this file
    empty_file_path = os.path.join(os.path.dirname(__file__), "empty.py")
    run_test(False, labels, grid, json, empty_file_path)
