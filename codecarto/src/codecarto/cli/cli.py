from __future__ import annotations
import click
from importlib_metadata import version
from ..errors import BaseNotFoundError, ThemeCreationError, MissingParameterError
from ..utils.dirs import MAIN_DIRECTORIES


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
    from ..code_cartographer import CodeCartographer

    CodeCartographer(file_path=import_name).main()


# TODO: this is debug code, remove later, or make dev an optional install argument?
# if it's intended for developer use, then should we just package this in?
@run.command("dir")
def dir():
    """Print the available directories."""
    from ..utils.dirs import print_all_directories

    print_all_directories()


@run.command("demo")
def demo():
    """Run the demo command."""
    from ..code_cartographer import CodeCartographer

    main_file_path = MAIN_DIRECTORIES["path"]
    CodeCartographer(main_file_path).main()


@run.command("new")
@click.argument("node_type")
@click.argument("base")
@click.argument("label")
@click.argument("shape")
@click.argument("size", type=int)
@click.argument("color")
@click.argument("alpha", type=int)
def new(node_type, base, label, shape, size, color, alpha):
    """
    Create a new theme with the specified parameters.

    Node type (str) : node type (e.g., str, For, ClassDef, FunctionDef)
    Base (str)      : base theme (e.g., basic.str, control.loop.for, datatype.class, datatype.function, etc.)
    Label (str)     : label for plot, will also be node_type (e.g., str, f, Cl, F, etc.)
    Shape (str)     : shape of plot
    Size (int)      : size of plot
    Color (str)     : color of plot
    Alpha (int)     : transparency of plot

    Example usage:
        codecarto new ClassDef datatype.class Cl o 10 red 10
    """
    from ..themes.themes import Theme

    theme = Theme()

    # check if all parameters are present
    if not all([node_type, base, label, shape, size, color, alpha]):
        raise MissingParameterError("New command requires all parameters.")
    node_type = theme.create_new_theme(
        node_type,
        base,
        label,
        shape,
        theme._sizes[size - 1],
        color,
        theme._alphas[alpha - 1],
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

    This function loads the theme data and prints each node type along with its corresponding properties,
    formatted with appropriate spacing.
    """
    from ..themes.themes import Theme

    theme = Theme()
    # Load theme data
    theme_data = {
        "bases": theme.bases,
        "labels": theme.labels,
        "shapes": theme.shapes,
        "sizes": theme.sizes,
        "colors": theme.colors,
        "alphas": theme.alphas,
    }

    # Check if theme_data is not empty
    if not theme_data:
        BaseNotFoundError("No node type data.")

    # Print node types
    print("\nNode types and properties:\n")
    for node_type in sorted(theme_data["bases"].keys()):
        base = theme_data["bases"][node_type]
        max_width = max(len(prop) for prop in theme_data.keys()) + 1
        print(f"{'Node_Type':{max_width}}  : {node_type}")
        print(f"    {'base':{max_width}}: {base}")
        for prop in theme_data.keys():
            if prop != "bases":
                print(f"    {prop:{max_width}}: {theme_data[prop][base]}")
        print("")
    print(
        """
Information:
    For a list of valid node types : https://docs.python.org/3/library/ast.html#abstract-grammar
    For a list of valid colors     : https://matplotlib.org/stable/gallery/color/named_colors.html
    For a list of valid shapes     : https://matplotlib.org/stable/api/markers_api.html
    """
    )


@run.command("themes")
@click.option(
    "--import",
    "-i",
    "import_path",
    metavar="FILEPATH",
    help="Import themes from a JSON file.",
)
@click.option(
    "--export",
    "-e",
    "export_dir",
    metavar="DIRECTORY",
    help="Export package themes.json to a directory.",
)
def themes(import_path: str, export_dir: str) -> None:
    """Print the available base themes and their corresponding properties.

    This function retrieves the path of the 'themes.json' file and prints its corresponding properties.
    If the file is in the current working directory, the output will indicate so.
    Additionally, this function can be used to import and export themes from/to a JSON file.

    Optional Args:
        import_path (str): The filepath of the JSON file to import themes from.
        export_dir (str): The directory to export the current themes to.
    """
    from ..themes.themes import Theme

    theme = Theme()
    # Handle import/export options
    if import_path:
        theme.import_theme(import_path)
        print(f"Themes imported from '{import_path}'.")
        return
    elif export_dir:
        theme.export_theme(export_dir)
        print(f"Themes exported to '{export_dir}'.")
        return

    # Load theme data
    theme_data = {
        "bases": theme.bases,
        "labels": theme.labels,
        "shapes": theme.shapes,
        "sizes": theme.sizes,
        "colors": theme.colors,
        "alphas": theme.alphas,
    }

    # Group the themes by base
    base_themes: dict[str, list] = {}
    for node_type in theme_data["bases"].keys():
        base = theme_data["bases"][node_type]
        if base not in base_themes:
            base_themes[base] = []
        base_themes[base].append(node_type)

    # print themes by base
    for base, node_types in base_themes.items():
        print(f"Base: {base}")
        max_width = max(len(prop) for prop in theme_data.keys()) + 1
        for prop in theme_data.keys():
            if prop != "bases":
                print(f"  {prop:{max_width}}: {theme_data[prop][base]}")
        print()
    print(
        f"\nBase themes and properties can be found in 'themes.json': {theme._theme_app_dir['path']}\n"
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
    codecarto themes [--types | -t | --new | -n | --import | -i | --export | -e]
    codecarto themes -n TYPE BASE LABEL SHAPE SIZE COLOR ALPHA 
    codecarto help

Command Description:
    FILE | FILE:APP  : The path of the Python file to visualize
    demo             : Runs the package on itself. 
    dir              : Show the various directories used by package.
    themes           : Show the directory of themes.json and shows current themes.
        -t TYPE      : Display the styles for all types or for a specific type.
        -n PARAMS    : Create a new theme with the specified parameters
        -i FILE_PATH : Import themes from a JSON file.
        -e DIRECOTRY : Export package themes.json to a directory.
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
