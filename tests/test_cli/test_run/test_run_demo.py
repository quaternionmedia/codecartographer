import pytest
import itertools
from run_helper import run_test


@pytest.mark.parametrize(
    "labels,grid,show,json",
    [args for args in itertools.product([False, True], repeat=4)],
)
def test_demo(labels, grid, show, json):
    """Test the run command with the demo file."""
    run_test(True, labels, grid, show, json)
