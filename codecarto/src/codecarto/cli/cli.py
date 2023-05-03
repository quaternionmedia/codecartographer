from __future__ import annotations
import click
import functools
from ..errors import BaseNotFoundError, ThemeCreationError, MissingParameterError


################### DEFAULTS 

def run_codecarto(import_name: str, json:bool, labels: bool, grid: bool, show:bool) -> None:
    from ..processor import Processor

    Processor(file_path=import_name, do_json=json, do_labels=labels, do_grid=grid, do_show=show).main()


def get_version():
    from ..utils.directory.package_dir import CODE_CARTO_PACKAGE_VERSION

    """Get the version of the codecarto package."""
    return CODE_CARTO_PACKAGE_VERSION


def print_help():
    """Print the usage information for the command-line interface.

    This function displays the usage information, examples, command list, and links to documentation
    for valid types, colors, and shapes.
    """
    help_text = """
Usage:
    codecarto demo 
                 -l | --labels (default True)
                 -g | --grid  (default False)
                 -s | --show  (default False)
                 -j | --json  (default False)
    codecarto dir
    codecarto help | -h | --help
    codecarto output -s | --set DIR
    codecarto FILE | FILE:APP 
                 -l | --labels (default False)
                 -g | --grid  (default False)
                 -s | --show  (default False)
                 -j | --json  (default False)
    codecarto palette 
                 -i | --import FILE
                 -e | --export DIR
                 -t | --types 
                 -n | --new PARAMS

Command Description:
    dir    : Show the various directories used by package.
    help   : Display this information
    output : Show the output directory.
        --set   | -s : Set the output directory to the provided directory.
        --reset | -r : Reset the output directory to the default directory.
    demo   : Runs the package on itself.  
    FILE   : The path of the Python file to visualize
        FILE & demo Options: 
           --labels | -l : Display labels on the graph. Default is False.
           --grid   | -g : Display a grid on the graph. Default is False.
           --show   | -s : Show the graph plot. Default is False.
           --json   | -j : Converts json data to graph and plots. Default is False.
        Examples:
           codecarto foo.py -l -g
           codecarto foo.py:MyApp -g
           codecarto module.foo -l
           codecarto module.foo:MyApp
    palette : Show the directory of palette.json and shows current themes.
        --import | -i  : Import palette from a provided JSON file path.
        --export | -e  : Export package palette.json to a provided directory. 
        --types  | -t  : Display the styles for all types or for a specific type.
        --new    | -n  : Create a new theme with the specified parameters.
                         PARAMS must be in the format: TYPE NAME SHAPE ALPHA COLOR SIZE
                         Example: 
                            codecarto palette -n ClassDef def.class Cl o 10 red 10 
         
New Theme Information:
    For a list of valid types      : https://docs.python.org/3/library/ast.html#abstract-grammar
    For a list of valid colors     : https://matplotlib.org/stable/gallery/color/named_colors.html
    For a list of valid shapes     : https://matplotlib.org/stable/api/markers_api.html
    Alpha must be an integer between 0 and 10. Represents [0.0, 0.1, 0.2., ... , 1.0] transparency.
    Size must be an integer between 0 and 10. Represents [100, 200, 300, ... , 1000] size.
    """
    print(help_text)


################### SETUP HELP GROUP


class CustomHelpGroup(click.Group):
    def get_help(self, ctx):
        return print_help()

    def parse_args(self, ctx, args):
        if "-h" in args:
            args.remove("-h")
            ctx.invoke(self.get_command(ctx, "help"))
            ctx.exit()
        super().parse_args(ctx, args)


################### RUN COMMAND


@click.group(cls=CustomHelpGroup)
@click.version_option(get_version())
def run() -> None:
    pass


################### SET UP SHARED COMMANDS


def shared_options(func):
    """Shared options for the run command."""
    @click.option(
        "--json",
        "-j",
        is_flag=True,
        help="Whether to convert json back to graph and plot.",
    )
    @click.option(
        "--labels",
        "-l",
        is_flag=True,
        help="Whether to show labels on plots.",
    )
    @click.option(
        "--grid",
        "-g",
        is_flag=True,
        help="Whether to have all plots in a grid layout.",
    )
    @click.option(
        "--show",
        "-s",
        is_flag=True,
        help="Whether to show plots.",
    )
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


################### RUN APP COMMAND


@run.command(
    context_settings={
        "ignore_unknown_options": True,
    },
)
@click.argument("import_name", metavar="FILE or FILE:APP")
@shared_options
def run_app(import_name: str, json: bool, labels: bool, grid: bool, show:bool) -> None:
    """Run CodeCartographer application.

    The code to run may be given as a path (ending with .py) or as a Python
    import, which will load the code and run an app called "app". You may optionally
    add a colon plus the class or class instance you want to run.

    Here are some examples:
        codecarto foo.py
        codecarto foo.py:MyApp
        codecarto module.foo
        codecarto module.foo:MyApp

    If you are running a file and want to pass command line arguments, wrap the filename and arguments
    in quotes:

        codecarto "foo.py arg --option"

    """
    run_codecarto(import_name, json, labels, grid, show)


@run.command("demo")
@shared_options
def demo(json:bool, labels: bool, grid: bool, show:bool):
    """Run the demo command."""
    from ..utils.directory.main_dir import MAIN_DIRECTORY

    main_file_path = MAIN_DIRECTORY["path"]
    # Call the run_app function with the main_file_path and labels/grid options
    run_codecarto(main_file_path, json, labels, grid, show)


################### DIR & HELP COMMAND


# TODO: this is debug code, remove later, or make dev an optional install argument?
# if it's intended for developer use, then should we just package this in by default?
@run.command("dir")
def dir():
    """Print the available directories."""
    from ..utils.directories import print_all_directories

    print_all_directories()

    # TODO: this is debug code, remove later, or make dev an optional install argument?
    print("Package Source Files:")
    from ..utils.directory.main_dir import MAIN_DIRECTORY
    from ..utils.directory.import_source_dir import get_all_source_files

    main_file_path = MAIN_DIRECTORY["path"]
    for path in get_all_source_files(main_file_path):
        # print every thing in the path after \dev\
        _path = path.split("\codecarto\\")[2]
        print(f"...carto\\{_path}")
    print()
 

@run.command("help")
def run_help():
    """Display usage information."""
    print_help()



################### OUTPUT COMMAND


@run.command("output")
@click.option(
    "--set",
    "-s",
    metavar="DIRECTORY",
    help="Set the output directory to a given file directory.",
)
@click.option(
    "--reset",
    "-r",
    is_flag=True,
    help="Set the output directory back to the package directory.",
)
def output(set: str, reset: bool):
    """Show the current output directory or change it."""
    if set:
        from ..utils.directory.output_dir import set_output_dir

        set_output_dir(set)
        print(f"Output directory changed to '{set}'.")

    elif reset:
        from ..utils.directory.output_dir import reset_output_dir

        _path = reset_output_dir()
        print(f"Output directory reset to '{_path}'.")
    else:
        from ..utils.directory.output_dir import get_output_dir

        current_output_dir = get_output_dir()
        print(f"Current output directory: '{current_output_dir}'.")


################### PALETTE COMMAND



@run.command("palette")
@click.option(
    "--import",
    "-i",
    "import_path",
    metavar="FILEPATH",
    help="Import palette from a JSON file.",
)
@click.option(
    "--export",
    "-e",
    "export_dir",
    metavar="DIRECTORY",
    help="Export package palette.json to a directory.",
)
@click.option(
    "--reset",
    "-r",
    "reset",
    is_flag=True,
    help="Reset the palette.json to the default_palette.json.",
)
@click.option(
    "--types",
    "-t",
    "types",
    is_flag=True,
    help="Print the available node types and their corresponding properties.",
)
@click.option(
    "--new",
    "-n",
    nargs=7,
    type=(str, str, str, str, int, str, int),
    help="Create a new theme with the specified parameters. 'codecarto -help' for more info.",
    metavar="TYPE BASE LABEL SHAPE SIZE COLOR ALPHA",
)
@click.pass_context
def palette(
    ctx, import_path: str, export_dir: str, reset: bool, new: bool, types: bool
) -> None:
    """Print the available base themes and their corresponding properties.

    This function retrieves the path of the 'palette.json' file and prints its corresponding properties.
    If the file is in the current working directory, the output will indicate so.
    Additionally, this function can be used to import and export a palette from/to a JSON file.

    Optional Args:
        import_path (str): The filepath of the JSON file to import a palette from.
        export_dir (str): The directory to export the current palette to.
        reset (bool): Whether to reset the palette.json to the default_palette.json.
        new (bool): Whether to create a new theme with the specified parameters.
        types (bool): Whether to print the available node types and their corresponding properties.
    """
    # Call the appropriate subcommand function
    from ..palette.palette import Palette

    palette = Palette()
    if import_path:
        palette_import(palette, import_path)
    elif export_dir:
        palette_export(palette, export_dir)
    elif reset:
        palette_reset(palette)
    elif types:
        palette_types(palette)
    elif new:
        palette_new_cmd = click.Command("palette_new", callback=palette_new)
        ctx.invoke(
            palette_new_cmd,
            **dict(
                zip(
                    ["node_type", "base", "label", "shape", "size", "color", "alpha"],
                    new,
                )
            ),
        )
    else:
        palette_print(palette)



################### PALETTE NEW COMMAND


@click.option(
    "--node_type", help="The node type (e.g., str, For, ClassDef, FunctionDef)."
)
@click.option(
    "--base",
    help="Base theme (e.g., basic.str, control.loop.for, datatype.class, datatype.function, etc.).",
)
@click.option(
    "--label",
    help="Label for plot, will also be node_type (e.g., str, f, Cl, F, etc.).",
)
@click.option("--shape", help="Shape of plot.")
@click.option("--size", type=int, help="Size of plot.")
@click.option("--color", help="Color of plot.")
@click.option("--alpha", type=int, help="Transparency of plot.")
def palette_new(node_type, base, label, shape, size, color, alpha):
    """
    Create a new theme with the specified parameters.

    Type (str)      : The node type (e.g., str, For, ClassDef, FunctionDef)
    Base (str)      : base theme (e.g., basic.str, control.loop.for, datatype.class, datatype.function, etc.)
    Label (str)     : label for plot, will also be node_type (e.g., str, f, Cl, F, etc.)
    Shape (str)     : shape of plot
    Size (int)      : size of plot
    Color (str)     : color of plot
    Alpha (int)     : transparency of plot

    Example usage:
        codecarto new ClassDef datatype.class Cl o 10 red 10
    """
    from ..palette.palette import Palette

    palette = Palette()

    # check if all parameters are present
    if not all([node_type, base, label, shape, size, color, alpha]):
        raise MissingParameterError("New command requires all parameters.")
    node_type = palette.create_new_theme(
        node_type,
        base,
        label,
        shape,
        palette._sizes[size - 1],
        color,
        palette._alphas[alpha - 1],
    )

    # check if node_type is None
    if node_type == None:
        raise ThemeCreationError("New theme could not be created.")


################### PALETTE COMMAND HELPERS


def palette_print(palette):
    """Print the available base themes and their corresponding properties.

    Prints the bases and base thems from the palette.json file.
    Also prints where the user's palette.json file is located.
    """

    # Load palette data
    palette_data = {
        "bases": palette.bases,
        "labels": palette.labels,
        "shapes": palette.shapes,
        "sizes": palette.sizes,
        "colors": palette.colors,
        "alphas": palette.alphas,
    }

    # Group the themes by base
    base_themes: dict[str, list] = {}
    for node_type in palette_data["bases"].keys():
        base = palette_data["bases"][node_type]
        if base not in base_themes:
            base_themes[base] = []
        base_themes[base].append(node_type)

    # print themes by base
    for base, node_types in base_themes.items():
        print(f"Base: {base}")
        max_width = max(len(prop) for prop in palette_data.keys()) + 1
        for prop in palette_data.keys():
            if prop != "bases":
                print(f"  {prop:{max_width}}: {palette_data[prop][base]}")
        print()
    print(
        f"\nBase themes and properties can be found in 'palette.json': {palette._palette_app_dir['path']}\n"
    )


def palette_import(palette, import_path):
    """Import a palette from a JSON file.

    Imports a palette from a JSON file and overwrites the current palette.

    Args:
        import_path (str): The filepath of the JSON file to import a palette from.
    """
    # ask the user to confirm import action
    if not click.confirm(
        "Are you sure you want to import a palette file? This will overwrite the current palette."
    ):
        return
    palette.import_palette(import_path)
    print(f"Palette imported from '{import_path}'.")


def palette_export(palette, export_dir):
    """Export the current palette to a JSON file.

    Exports the current palette to a JSON file in the specified directory.

    Args:
        export_dir (str): The directory to export the current palette to.
    """
    palette.export_palette(export_dir)
    print(f"Palette exported to '{export_dir}'.")


def palette_reset(palette):
    """Reset the palette to the default palette.

    Resets the palette to the package's default palette.
    """
    # ask the user to confirm reset action
    if not click.confirm(
        "Are you sure you want to reset the palette to the default palette?"
    ):
        return
    palette.reset_palette()
    print(f"Palette reset to default.")
    return


def palette_types(palette):
    """Print the available node types and their corresponding properties.

    This function loads the palette data and prints each node type along with its corresponding properties,
    formatted with appropriate spacing.
    """
    # Load palette data
    palette_data = {
        "bases": palette.bases,
        "labels": palette.labels,
        "shapes": palette.shapes,
        "sizes": palette.sizes,
        "colors": palette.colors,
        "alphas": palette.alphas,
    }

    # Check if palette_data is not empty
    if not palette_data:
        BaseNotFoundError("No node type data.")

    # Print node types
    print("\nNode types and properties:\n")
    for node_type in sorted(palette_data["bases"].keys()):
        base = palette_data["bases"][node_type]
        max_width = max(len(prop) for prop in palette_data.keys()) + 1
        print(f"{'Node_Type':{max_width}}  : {node_type}")
        print(f"    {'base':{max_width}}: {base}")
        for prop in palette_data.keys():
            if prop != "bases":
                print(f"    {prop:{max_width}}: {palette_data[prop][base]}")
        print("")
    print(
        """
Information:
    For a list of valid node types : https://docs.python.org/3/library/ast.html#abstract-grammar
    For a list of valid colors     : https://matplotlib.org/stable/gallery/color/named_colors.html
    For a list of valid shapes     : https://matplotlib.org/stable/api/markers_api.html
    """
    )
