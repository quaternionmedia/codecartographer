import os
import tempfile
import itertools
import matplotlib.pyplot as plt
import matplotlib._pylab_helpers as pylab_helpers
from pathlib import Path

from ...src.codecarto.processor import process
from ...src.codecarto.config.directory.output_dir import set_output_dir
from ...src.codecarto.config.directory.package_dir import PROCESSOR_FILE_PATH


def test_processor():
    """Test Processor's outputs exist with all options."""
    try:
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            for json, labels, grid, show in itertools.product([False, True], repeat=4):
                # Turn off interactive mode so plt.show() doesn't block the test
                plt.ioff()

                # Run demo command
                set_output_dir(Path(temp_dir), ask_user=False)
                output_dirs: dict = process(
                    source=PROCESSOR_FILE_PATH,
                    json=json,
                    labels=labels,
                    grid=grid,
                    show=show,
                )

                # Check if demo closed the plot
                closed_plots = len(pylab_helpers.Gcf.get_all_fig_managers()) == 0

                # Turn interactive mode back on so the test can continue
                plt.ion()

                # Check if the plot was closed
                assert closed_plots

                # Check if the main directories exist
                assert os.path.exists(output_dirs["output_dir"])
                assert os.path.exists(output_dirs["version_dir"])
                assert os.path.exists(output_dirs["graph_dir"])
                assert os.path.exists(output_dirs["graph_code_dir"])
                assert os.path.exists(output_dirs["graph_json_dir"])
                assert os.path.exists(output_dirs["json_dir"])

                # Check if the JSON file exists
                assert os.path.exists(output_dirs["json_graph_file_path"])

                # Check if at least one plot file is created in the graph_code_dir
                plot_files = [
                    f
                    for f in os.listdir(output_dirs["graph_code_dir"])
                    if f.endswith(".png")
                ]
                assert len(plot_files) > 0

                # Check if only one plot file is created in the graph_code_dir when grid is True
                if grid == True:
                    assert len(plot_files) == 1
                else:
                    assert (
                        len(plot_files) > 1
                    )  # should get at least 2 plots when grid is False

                # Check if at least one plot file is created in the graph_json_dir
                if json == True:
                    plot_files = [
                        f
                        for f in os.listdir(output_dirs["graph_json_dir"])
                        if f.endswith(".png")
                    ]
                    assert len(plot_files) > 0

                    # Check if only one plot file is created in the graph_code_dir when grid is True
                    if grid == True:
                        assert len(plot_files) == 1
                    else:
                        assert (
                            len(plot_files) > 1
                        )  # should get at least 2 plots when grid is False
    except Exception as e:
        # Raise the exception
        raise e
