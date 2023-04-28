from __future__ import annotations
import click
from importlib_metadata import version
from ..errors import BaseNotFoundError, ThemeCreationError, MissingParameterError
from ..utils.directories import MAIN_DIRECTORIES


@click.group()
@click.version_option(version("codecarto"))
def run():
    pass


@run.command(
    context_settings={
        "ignore_unknown_options": True,
    },
)
@click.argument("import_name", metavar="FILE or FILE:APP")
def run_app(import_name: str) -> None:
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
    from ..processor import Processor

    Processor(file_path=import_name).main()


# TODO: this is debug code, remove later, or make dev an optional install argument?
# if it's intended for developer use, then should we just package this in?
@run.command("dir")
def dir():
    """Print the available directories."""
    from ..utils.directories import print_all_directories

    print_all_directories()


@run.command("demo")
def demo():
    """Run the demo command."""
    from ..processor import Processor

    main_file_path = MAIN_DIRECTORIES["path"]
    Processor(main_file_path).main()


@run.command("new")
@click.argument("type")
@click.argument("base")
@click.argument("label")
@click.argument("shape")
@click.argument("size", type=int)
@click.argument("color")
@click.argument("alpha", type=int)
def new(node_type, base, label, shape, size, color, alpha):
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
    print(
        f"New theme '{node_type}' created with parameters: base={base}, label={label}, shape={shape}, size={size}, color={color}, alpha={alpha}"
    )


@run.command("types")
def print_node_types():
    """Print the available node types and their corresponding properties.

    This function loads the palette data and prints each node type along with its corresponding properties,
    formatted with appropriate spacing.
    """
    from ..palette.palette import Palette

    palette = Palette()
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
def palette(import_path: str, export_dir: str, reset: bool) -> None:
    """Print the available base themes and their corresponding properties.

    This function retrieves the path of the 'palette.json' file and prints its corresponding properties.
    If the file is in the current working directory, the output will indicate so.
    Additionally, this function can be used to import and export a palette from/to a JSON file.

    Optional Args:
        import_path (str): The filepath of the JSON file to import a palette from.
        export_dir (str): The directory to export the current palette to.
    """
    from ..palette.palette import Palette

    palette = Palette()
    # Handle import/export/reset options
    if import_path:
        # ask the user to confirm import action
        if not click.confirm(
            "Are you sure you want to import a palette file? This will overwrite the current palette."
        ):
            return
        palette.import_palette(import_path)
        print(f"Palette imported from '{import_path}'.")
        return
    elif export_dir:
        palette.export_palette(export_dir)
        print(f"Palette exported to '{export_dir}'.")
        return
    elif reset:
        # ask the user to confirm reset action
        if not click.confirm(
            "Are you sure you want to reset the palette to the default palette?"
        ):
            return
        palette.reset_palette()
        print(f"Palette reset to default.")
        return

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


@run.command("help")
def print_help():
    """Print the usage information for the command-line interface.

    This function displays the usage information, examples, command list, and links to documentation
    for valid types, colors, and shapes.
    """
    # Print help text
    help_text = """
Usage:
    codecarto FILE | FILE:APP 
    codecarto demo
    codecarto dir
    codecarto palette [--types | -t | --new | -n | --import | -i | --export | -e]
    codecarto palette -n TYPE BASE LABEL SHAPE SIZE COLOR ALPHA 
    codecarto help

Command Description:
    FILE | FILE:APP  : The path of the Python file to visualize
    demo             : Runs the package on itself. 
    dir              : Show the various directories used by package.
    palette          : Show the directory of palette.json and shows current themes.
        -t TYPE      : Display the styles for all types or for a specific type.
        -n PARAMS    : Create a new theme with the specified parameters
        -i FILE_PATH : Import palette from a JSON file.
        -e DIRECOTRY : Export package palette.json to a directory.
    help             : Display usage information

File Examples:
    codecarto foo.py
    codecarto foo.py:MyApp
    codecarto module.foo
    codecarto module.foo:MyApp

New Theme Example:
    codecarto new ClassDef datatype.class Cl o 10 red 10

New Theme Information:
    For a list of valid types      : https://docs.python.org/3/library/ast.html#abstract-grammar
    For a list of valid colors     : https://matplotlib.org/stable/gallery/color/named_colors.html
    For a list of valid shapes     : https://matplotlib.org/stable/api/markers_api.html
    Alpha must be an integer between 0 and 10.
    Size must be an integer between 0 and 10.

    """
    print(help_text)
