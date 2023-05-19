import pytest
import itertools
from cli_run_helper import run_test


@pytest.mark.parametrize(
    "labels,grid,json",
    [args for args in itertools.product([False, True], repeat=3)],
)
def test_demo(labels, grid, json):
    """Test the run command with the demo file."""
    run_test(True, labels, grid, json)
