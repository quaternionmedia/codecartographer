import os
import nox
import json
import shutil
import tempfile
import itertools
import subprocess

# TODO: make checks when user says no to prmopts


def get_palette_data(item: str, appdata: bool = True) -> dict | str:
    """Load the palette data from the Palette class."""
    from src.codecarto.palette.palette import Palette

    if item == "bases":
        return Palette().get_palette_data()
    elif item == "path" and appdata is True:
        return Palette()._palette_app_dir[item]
    elif item == "path" and appdata is False:
        return Palette()._palette_pack_dir[item]


# tests if package can be installed on python 3.8, 3.9 and 3.11
@nox.session(python=["3.8", "3.9", "3.11"])
def unit_tests(session):
    session.install(".")
    session.install("matplotlib")  # needed to close the matplot show window
    session.install("pytest")
    session.run("pytest", "tests")


# tests package command dir:
@nox.session
def test_dir(session):
    """Test that expected print statements are printed when running the dir command."""
    session.install(".")
    result = subprocess.run(["codecarto", "dir"], capture_output=True, text=True)

    # Check if certain strings are in the directory section
    expected_strings = [
        "appdata_dir",
        "codecarto_appdata_dir",
        "package_dir",
        "config_dirs",
        "main_dirs",
        "palette_dirs",
        "output_dirs",
        "version",
        "output_dir",
        "version_dir",
        "graph_dir",
        "graph_code_dir",
        "graph_json_dir",
        "json_dir",
        "json_graph_file_path",
        "Package Source Python Files:",
    ]
    for string in expected_strings:
        assert string in result.stdout

    # Check if key files are in the package source files section
    key_files = [
        "errors.py",
        "parser.py",
        "plotter.py",
        "processor.py",
        "palette.py",
        "json_graph.py",
        "json_utils.py",
        "cli.py",
        "config.py",
        "directories.py",
        "utils.py",
        "appdata_dir.py",
        "config_dir.py",
        "import_source_dir.py",
        "main_dir.py",
        "output_dir.py",
        "package_dir.py",
        "palette_dir.py",
    ]
    for string in key_files:
        assert string in result.stdout


# tests package command help:
@nox.session
def test_help(session):
    session.install(".")

    commands = [
        ["codecarto", "help"],
        ["codecarto", "-h"],
        ["codecarto", "--help"],
    ]

    for command in commands:
        result = subprocess.run(*command, capture_output=True, text=True)

        expected_strings = [
            "Usage:",
            "codecarto demo",
            "-l | --labels (default True)",
            "-g | --grid  (default False)",
            "-s | --show  (default False)",
            "-j | --json  (default False)",
            "codecarto dir",
            "codecarto help | -h | --help",
            "codecarto output -s | --set DIR",
            "codecarto FILE",
            "codecarto palette",
            "-i | --import FILE",
            "-e | --export DIR",
            "-t | --types",
            "-n | --new PARAMS",
            "Command Description:",
            "dir    : Show the various directories used by package.",
            "help   : Display this information",
            "output : Show the output directory.",
            "--set   | -s : Set the output directory to the provided directory.",
            "--reset | -r : Reset the output directory to the default directory.",
            "demo   : Runs the package on itself.",
            "FILE   : The path of the Python file to visualize",
            "FILE & demo Options:",
            "--labels | -l : Display labels on the graph. Default is False.",
            "--grid   | -g : Display a grid on the graph. Default is False.",
            "--show   | -s : Show the graph plot. Default is False.",
            "--json   | -j : Converts json data to graph and plots. Default is False.",
            "Examples:",
            "codecarto foo.py -l --grid --json",
            "codecarto demo -labels -g -show",
            "palette : Show the directory of palette.json and shows current themes.",
            "--import | -i  : Import palette from a provided JSON file path.",
            "--export | -e  : Export package palette.json to a provided directory.",
            "--types  | -t  : Display the styles for all types or for a specific type.",
            "--new    | -n  : Create a new theme with the specified parameters.",
            "Examples:",
            "codecarto palette -n ClassDef def.class Cl o 10 red 10",
            "codecarto palette --export EXPORT_DIR",
            "codecarto palette -i IMPORT_FILE",
            "New Theme Information:",
            "For a list of valid types      : https://docs.python.org/3/library/ast.html#abstract-grammar",
            "For a list of valid colors     : https://matplotlib.org/stable/gallery/color/named_colors.html",
            "For a list of valid shapes     : https://matplotlib.org/stable/api/markers_api.html",
            "Alpha must be an integer between 0 and 10. Represents [0.0, 0.1, 0.2., ... , 1.0] transparency.",
            "Size must be an integer between 0 and 10. Represents [100, 200, 300, ... , 1000] size.",
        ]
        for string in expected_strings:
            assert string in result.stdout


# tests package command output:
@nox.session
def test_output(session):
    session.install(".")

    with tempfile.TemporaryDirectory() as temp_dir:
        commands = [
            ["codecarto", "output"],
            ["codecarto", "-s", temp_dir],
            ["codecarto", "--set", temp_dir],
            ["codecarto", "-r"],
            ["codecarto", "--reset"],
        ]

        for command in commands:
            result = subprocess.run(
                *command, input="y\n", capture_output=True, text=True
            )

            if command == ["codecarto", "output"]:
                # output directory
                assert "Current output directory: " in result.stdout
                # check if the path exists
                path = result.stdout.split("Current output directory: ")[1]
                assert os.path.exists(path)
            elif command == ["codecarto", "-s", temp_dir] or command == [
                "codecarto",
                "--set",
                temp_dir,
            ]:
                # set output directory
                assert "Output directory changed to " in result.stdout
                # check if the path exists
                path = result.stdout.split("Output directory changed to ")[1]
                assert os.path.exists(path)
            elif command == ["codecarto", "-r"] or command == ["codecarto", "--reset"]:
                # reset output directory
                assert "Output directory reset to " in result.stdout
                # check if the path exists
                path = result.stdout.split("Output directory reset to ")[1]
                assert os.path.exists(path)

            # check the config file
            # get the config file in the \src\codecarto\ directory
            config_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "src\\codecarto\\config.json",
            )
            with open(config_file, "r") as f:
                config = json.load(f)
            # check if the output directory is the same as the one in the config file
            assert config["output_dir"] == path


# tests package command output (yes):
@nox.session()
def test_output_dir_yes(session):
    session.install(".")

    with tempfile.TemporaryDirectory() as temp_dir:
        non_existent_dir = os.path.join(temp_dir, "not_here")
        command = f"codecarto output -s {non_existent_dir}"

        # Run the command and send the input "y\n"
        result = subprocess.run(
            command, input="y\n", text=True, capture_output=True, shell=True
        )

        # Check if the output contains the expected prompt question and response
        assert (
            "The new output directory does not exist. Would you like to make it? (y/n)"
            in result.stdout
        )
        assert f"Output directory changed to '{non_existent_dir}'" in result.stdout


# tests package command output (no):
@nox.session()
def test_output_dir_no(session):
    session.install(".")

    with tempfile.TemporaryDirectory() as temp_dir:
        non_existent_dir = os.path.join(temp_dir, "not_here")
        command = f"codecarto output -s {non_existent_dir}"

        # Run the command and send the input "n\n"
        result = subprocess.run(
            command, input="n\n", text=True, capture_output=True, shell=True
        )

        # Check if the output contains the expected prompt question and response
        assert (
            "The new output directory does not exist. Would you like to make it? (y/n)"
            in result.stdout
        )
        assert "Exiting" in result.stdout


# tests package command palette:
@nox.session
def test_palette(session):
    session.install(".")
    result = subprocess.run("codecarto", "palette", capture_output=True, text=True)

    # define the expected strings
    palette_path = get_palette_data("path")
    expected_strings = [
        f"Base themes and properties can be found in 'palette.json': {palette_path}"
    ]

    # check if the expected strings are in the output
    for string in expected_strings:
        assert string in result.stdout

    # Load palette data
    palette_data = get_palette_data("bases")

    # Group the themes by base
    base_themes: dict[str, list] = {}
    for node_type in palette_data["bases"].keys():
        base = palette_data["bases"][node_type]
        if base not in base_themes:
            base_themes[base] = []
        base_themes[base].append(node_type)

    # print themes by base
    data: str = ""
    for base, node_types in base_themes.items():
        max_width = max(len(prop) for prop in palette_data.keys()) + 1
        data += f"{'Base     ':{max_width}}: {base}\n"
        for prop in palette_data.keys():
            if prop != "bases":
                data += f"  {prop:{max_width}}: {palette_data[prop][base]}\n"

    # check if the base style string is in the output
    assert data in result.stdout


# tests package command palette with option:
@nox.session
def test_palette_import(session):
    session.install(".")

    with tempfile.TemporaryDirectory() as temp_dir:
        # create a temporary file
        temp_file = os.path.join(temp_dir, "test_palette_import.json")

        # get the default palette
        palette_path = get_palette_data("path", False)

        # copy the default palette to the temporary directory
        shutil.copy(palette_path, temp_file)

        # define commands
        commands = [
            ["codecarto", "palette", "-i", temp_file],
            ["codecarto", "palette", "--import", temp_file],
        ]

        # run commands
        for command in commands:
            result = subprocess.run(*command, capture_output=True, text=True)
            assert "Palette imported from " in result.stdout

        # check if the palette file is the same as the default palette
        with open(palette_path, "r") as f:
            default_palette = json.load(f)
        with open(temp_file, "r") as f:
            imported_palette = json.load(f)
        assert default_palette == imported_palette


# tests package command palette with export option:
@nox.session
def test_palette_export(session):
    session.install(".")

    with tempfile.TemporaryDirectory() as temp_dir:
        # create a temporary file
        temp_file = os.path.join(temp_dir, "test_palette_export.json")

        # define commands
        commands = [
            ["codecarto", "palette", "-e", temp_file],
            ["codecarto", "palette", "--export", temp_file],
        ]

        # run commands
        for command in commands:
            result = subprocess.run(*command, capture_output=True, text=True)
            assert "Palette exported to " in result.stdout

        # get the default palette
        palette_path = get_palette_data("path", False)

        # check if the palette file is the same as the default palette
        with open(palette_path, "r") as f:
            default_palette = json.load(f)
        with open(temp_file, "r") as f:
            exported_palette = json.load(f)
        assert default_palette == exported_palette


# tests package command palette with reset option:
@nox.session
def test_palette_reset(session):
    session.install(".")

    with tempfile.TemporaryDirectory() as temp_dir:
        # define commands
        commands = [
            ["codecarto", "palette", "-r"],
            ["codecarto", "palette", "--reset"],
        ]

        # run commands
        for command in commands:
            result = subprocess.run(*command, capture_output=True, text=True)
            assert "Palette reset to default." in result.stdout

        # get the default palette
        default_palette_path = get_palette_data("path", False)

        # get the appdata palette
        appdata_palette_path = get_palette_data("path")

        # check if the palette file is the same as the default palette
        with open(default_palette_path, "r") as f:
            default_palette = json.load(f)
        with open(appdata_palette_path, "r") as f:
            appdata_palette = json.load(f)
        assert default_palette == appdata_palette


# tests package command palette with types option:
@nox.session
def test_palette_types(session):
    session.install(".")

    # define commands
    commands = [
        ["codecarto", "palette", "-t"],
        ["codecarto", "palette", "--types"],
    ]

    # define expected strings
    expected_strings = [
        "Node types and properties:",
        "Information:",
        "For a list of valid types      : https://docs.python.org/3/library/ast.html#abstract-grammar",
        "for a list of valid colors     : https://matplotlib.org/stable/gallery/color/named_colors.html",
        "for a list of valid shapes     : https://matplotlib.org/stable/api/markers_api.html",
    ]

    # run commands
    for command in commands:
        result = subprocess.run(*command, capture_output=True, text=True)
        for string in expected_strings:
            assert string in result.stdout

        # Check that the bases are in the output
        palette_data = get_palette_data("bases")

        # Print node types
        data: str = ""
        for node_type in sorted(palette_data["bases"].keys()):
            base = palette_data["bases"][node_type]
            max_width = max(len(prop) for prop in palette_data.keys()) + 1
            data += f"{'Node_Type':{max_width}}  : {node_type}\n"
            data += f"    {'base':{max_width}}: {base}\n"
            for prop in palette_data.keys():
                if prop != "bases":
                    data += f"    {prop:{max_width}}: {palette_data[prop][base]}\n"

        # check if the base style string is in the output
        assert data in result.stdout


# tests package command palette with new option:
@nox.session
def test_palette_new(session):
    session.install(".")

    with tempfile.TemporaryDirectory() as temp_dir:
        # create a temporary file
        temp_file = os.path.join(temp_dir, "test_palette_new.json")

        # define commands
        commands = [
            [
                "codecarto",
                "palette",
                "-n",
                "Type_Test_Short",
                "basic",
                "Label_Test_Short",
                "o",
                "red",
                "3",
                "1",
            ],
            [
                "codecarto",
                "palette",
                "--new",
                "Type_Test_Long",
                "basic",
                "Label_Test_Long",
                "s",
                "blue",
                "4",
                "2",
            ],
        ]

        # run commands
        run_commands_and_check_output(commands)

        # check that the new themes are in the palette
        check_palette_data(commands)

        # reset palette
        subprocess.run("codecarto", "palette", "-r", silent=True)

        # check that the new themes are not in the palette anymore
        check_palette_data(commands, presence=False)

        def run_commands_and_check_output(commands):
            for command in commands:
                result = subprocess.run(*command, capture_output=True, text=True)
                expected_strings = [
                    f"New theme added to palette: ",
                    (
                        f"New theme '{command[0]}' "
                        f"created with parameters: "
                        f"base={command[1]}, "
                        f"label={command[2]}, "
                        f"shape={command[3]}, "
                        f"color={command[5]}, "
                        f"size={command[4]}, "
                        f"alpha={command[6]}"
                    ),
                ]
                for string in expected_strings:
                    assert string in result.stdout

        def check_palette_data(commands, presence=True):
            palette_data = get_palette_data

            for command in commands:
                assert (command[0] in palette_data["bases"]) == presence
                assert (command[1] in palette_data["labels"]) == presence
                assert (command[2] in palette_data["shapes"]) == presence
                assert (command[4] in palette_data["colors"]) == presence
                assert (command[3] in palette_data["sizes"]) == presence
                assert (command[5] in palette_data["alphas"]) == presence


# tests package command demo: with all options
@nox.session
@nox.parametrize(
    "labels,grid,show,json",
    [args for args in itertools.product([False, True], repeat=4)],
)
def test_demo(session, labels, grid, show, json):
    run_test(session, True, labels, grid, show, json)


# tests package command demo: with all options
@nox.session
@nox.parametrize(
    "labels,grid,show,json",
    [args for args in itertools.product([False, True], repeat=4)],
)
def test_empty(session, labels, grid, show, json):
    import os

    # define dempty file path in tests directory
    empty_file_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "tests\\empty.py"
    )

    # define expected strings
    expected_strings: list = [
        "Code Cartographer:",
        "Processing File:",
        empty_file_path,
        "Visited Tree",
        "No graph to plot",
    ]

    # define options
    options_short = []
    options_long = []
    if labels:
        options_short.append("-l")
        options_long.append("--labels")
    if grid:
        options_short.append("-g")
        options_long.append("--grid")
    if show:
        options_short.append("-s")
        options_long.append("--show")
    if json:
        options_short.append("-j")
        options_long.append("--json")

    # run commands and check output
    session.install(".")
    for i in range(2):
        if i == 0:
            result = subprocess.run(
                "codecarto",
                empty_file_path,
                *options_short,
                capture_output=True,
                text=True,
                check=True,
            )
            for string in expected_strings:
                assert string in result.stdout
        else:
            result = subprocess.run(
                "codecarto",
                empty_file_path,
                *options_long,
                capture_output=True,
                text=True,
                check=True,
            )
            for string in expected_strings:
                assert string in result.stdout


# tests package command with file: with all options
@nox.session
@nox.parametrize(
    "labels,grid,show,json",
    [args for args in itertools.product([False, True], repeat=4)],
)
def test_file(session, labels, grid, show, json):
    run_test(session, False, labels, grid, show, json)


def run_test(session, demo, labels, grid, show, json):
    # get demo file path
    from src.codecarto.utils.directory.main_dir import MAIN_DIRECTORY

    demo_file_path = MAIN_DIRECTORY["path"]

    # define static strings
    starting_strings: list = [
        "Code Cartographer:",
        "Processing File:",
        demo_file_path,
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

    # define options
    options_short = []
    options_long = []
    add_running_strings: bool = False
    add_json_strings: bool = False
    add_grid_strings: bool = False
    if labels:
        options_short.append("-l")
        options_long.append("--labels")
        add_running_strings = True
    if grid:
        options_short.append("-g")
        options_long.append("--grid")
        add_running_strings = True
        add_grid_strings = True
    if show:
        options_short.append("-s")
        options_long.append("--show")
        add_running_strings = True
    if json:
        options_short.append("-j")
        options_long.append("--json")
        add_json_strings = True

    # define expected strings
    expected_strings: list = starting_strings
    if add_running_strings:
        expected_strings += running_strings
    if add_json_strings:
        expected_strings += json_strings
    if add_grid_strings:
        expected_strings += grid_strings

    # run commands and check output
    if demo:
        run_argument = "demo"
    else:
        run_argument = demo_file_path
    session.install(".")
    for i in range(2):
        if i == 0:
            result = subprocess.run(
                "codecarto",
                run_argument,
                *options_short,
                capture_output=True,
                text=True,
                check=True,
            )
            for string in expected_strings:
                assert string in result.stdout
        else:
            result = subprocess.run(
                "codecarto",
                run_argument,
                *options_long,
                capture_output=True,
                text=True,
                check=True,
            )
            for string in expected_strings:
                assert string in result.stdout
