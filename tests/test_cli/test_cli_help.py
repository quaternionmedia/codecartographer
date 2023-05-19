import subprocess
import tempfile 

def test_help():
    """Test the help command."""
    with tempfile.TemporaryDirectory() as temp_dir:
        commands = [
            ["codecarto", "help"],
            ["codecarto", "-h"],
            ["codecarto", "--help"],
        ]

        for command in commands:
            result = subprocess.run(command, capture_output=True, text=True)

            expected_strings = [
                "Usage:",
                "codecarto demo",
                "-l | --labels (default True)",
                "-g | --grid  (default False)",
                "-s | --show  (default False)",
                "-j | --json  (default False)",
                "-d | --dir   (default False)",
                "-u | --uno  (default False)",
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
                "--dir    | -d : Prints passed file's source code to be used in process.",
                "Does NOT run the package. Default is False.",
                "--uno    | -u : Whether to run for a single file or all of source directory. Default is False.",
                "Examples:",
                "codecarto foo.py -l --grid --json",
                "codecarto demo -labels -g -show",
                "palette : Show the directory of palette.json and shows current themes.",
                "--import | -i  : Import palette from a provided JSON file path.",
                "--export | -e  : Export package palette.json to a provided directory.",
                "--types  | -t  : Display the styles for all types or for a specific type.",
                "--new    | -n  : Create a new theme with the specified parameters.",
                "PARAMS must be in the format: TYPE NAME SHAPE COLOR SIZE ALPHA",
                "Examples:",
                "codecarto palette -n ClassDef def.class Cl o red 5 10",
                "codecarto palette --export EXPORT_DIR",
                "codecarto palette -i IMPORT_FILE",
                "New Theme Information:",
                "For a list of valid types      : https://docs.python.org/3/library/ast.html#abstract-grammar",
                "For a list of valid shapes     : https://matplotlib.org/stable/api/markers_api.html",
                "For a list of valid colors     : https://matplotlib.org/stable/gallery/color/named_colors.html",
                "Size must be an integer between 0 and 10. Represents [100, 200, 300, ... , 1000] size.",
                "Alpha must be an integer between 0 and 10. Represents [0.0, 0.1, 0.2., ... , 1.0] transparency.",
            ]
            for string in expected_strings:
                # the string does not include the newline character or spacing 
                # so we need to check that the 'string' is in the result.stdout
                # but not exactly equal to the result.stdout
                assert string in result.stdout
