import pytest
import itertools
from cli_run_helper import run_test


@pytest.mark.parametrize(
    "labels,grid,json", 
    [args for args in itertools.product([False, True], repeat=3)]
)
def test_file(labels, grid, json):
    """Test the run command with a file."""
    run_test(False, labels, grid, json)
