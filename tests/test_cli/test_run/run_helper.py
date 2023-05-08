import subprocess
import tempfile


def run_test(demo, labels, grid, show, json, file_path=None):
    """Run the test for the demo/file command."""
    with tempfile.TemporaryDirectory() as temp_dir:
        from codecarto import MAIN_DIRECTORY

        # define file path
        _file_path: str = file_path if file_path is not None else MAIN_DIRECTORY["path"]

        # define static strings
        starting_strings: list = [
            "Code Cartographer:",
            "Processing File:",
            _file_path,
            "Visited Tree",
        ]
        running_strings: list = [
            "Plotting Code Graph",
            "Code Plots Saved",
            "Finished",
            "Output Directory:",
        ]
        json_strings: list = [
            "Plotting JSON Graph",
            "JSON Plots Saved",
        ]
        grid_strings: list = [
            "Plotting grid...",
        ]
        no_graph_strings: list = [
            "No graph to plot",
        ]

        # define options and options related strings
        # 'condition' is used to determine if the option should be added
        options_data = {
            "labels": {
                "short": "-l",
                "long": "--labels",
                "strings": running_strings,
                "condition": labels,
            },
            "grid": {
                "short": "-g",
                "long": "--grid",
                "strings": running_strings + grid_strings,
                "condition": grid,
            },
            "show": {
                "short": "-s",
                "long": "--show",
                "strings": running_strings,
                "condition": show,
            },
            "json": {
                "short": "-j",
                "long": "--json",
                "strings": json_strings,
                "condition": json,
            },
        }

        # add options to lists and expected strings
        options_short = []
        options_long = []
        expected_strings = starting_strings
        for key, data in options_data.items():
            if data["condition"]:
                options_short.append(data["short"])
                options_long.append(data["long"])
                expected_strings += data["strings"]

        # add empty strings if file path is given
        if file_path is not None:
            expected_strings += no_graph_strings

        # convert back to list to remove duplicates
        expected_strings = list(expected_strings)

        # run commands and check output
        run_argument: str = "demo" if demo else _file_path

        # run commands
        for options in [options_short, options_long]:
            result = subprocess.run(
                ["codecarto", run_argument, *options],
                capture_output=True,
                text=True,
                check=True,
            )
            for string in expected_strings:
                assert string in result.stdout
