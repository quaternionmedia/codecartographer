import pytest
import itertools
from run_helper import run_test


@pytest.mark.parametrize(
    "labels,grid,show,json",
    [args for args in itertools.product([False, True], repeat=4)],
)
def test_file(labels, grid, show, json):
    """Test the run command with a file."""
    run_test(False, labels, grid, show, json)
