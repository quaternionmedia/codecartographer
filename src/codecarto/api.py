import networkx as nx

from .config.config import Config
from .json.json_graph import JsonGraph
from .palette.palette import Palette
from .parser import SourceParser
from .processor import Processor
from .plotter import GraphPlot
from .json.json_utils import save_json_file, load_json_file
from .utils.directory.import_source_dir import get_all_source_files


class CodeCarto:
    def __init__(
        self,
        source_files: list = None,
        output_dir: str = None,
        palette_file_path: str = None,
    ):
        self.source: list = source_files
        self.output_dir: str = output_dir
        self.palette = Palette()
        if palette_file_path is not None:
            self.palette.load_palette(palette_file_path)
        self.parser = None
        self.graph = None
        self.plotter = None

    ########### PARSER #####################
    def parse_source(self, source: str | list = None) -> nx.DiGraph:
        """Parses a source file or list of source files into a networkx graph.

        Args:
        -----
            source (str): The source file to get the source files from, then parse. \n
            Or source (list): The list of source files to parse.

        Returns:
        --------
            nx.DiGraph: The networkx graph.
        """
        source = self.source if source is None else source
        if source is None:
            raise ValueError("No source provided.")
        if isinstance(source, str):
            source = self.get_source_files(source)
        self.parser: SourceParser = SourceParser(source)
        self.graph = self.parser.graph
        return self.graph

    ########### PLOTTER ####################
    def plot(self, graph: nx.DiGraph, layout: str = "", _grid: bool = False) -> str:
        """Plots a networkx graph.

        Args:
        -----
            graph (nx.DiGraph): The networkx graph to plot. \n
            layout (str): The layout to use for the plot. \n
            _grid (bool): Whether or not plot all layouts in a grid.

        Returns:
        --------
            str: The output directory of the plots.
        """
        graph = self.graph if graph is None else graph
        if graph is None:
            raise ValueError("No graph provided.")
        if self.plotter is None:
            self._set_plotter(_grid)
        self.plotter.plot(graph, layout)
        return self.plotter.dirs["output_dir"]

    def _set_plotter(self, _grid: bool = False) -> GraphPlot:
        """Sets the plotter to a GraphPlot object.

        Args:
        -----
            _grid (bool): Whether or not to plot all layouts in a grid.

        Returns:
        --------
            GraphPlot: The GraphPlot object.
        """
        if self.plotter is None:
            self.plotter = GraphPlot(do_grid=_grid)
        if _grid:
            self.plotter.do_grid = True
        return self.plotter

    ########### JSON #######################
    def convert_graph_to_json(self, graph: nx.DiGraph) -> dict:
        """Converts a networkx graph to a json serializable object.

        Args:
        -----
            graph (nx.DiGraph): The networkx graph to convert to json.

        Returns:
        --------
            dict: The json serializable object.
        """
        graph = self.graph if graph is None else graph
        if graph is None:
            raise ValueError("No graph provided.")
        return JsonGraph.graph_to_json(graph)

    def convert_json_to_graph(self, json: dict) -> nx.DiGraph:
        """Converts a json object to a networkx graph.

        Args:
        -----
            json (dict): The json object to convert to a networkx graph.

        Returns:
        --------
            nx.DiGraph: The networkx graph.
        """
        json = self.graph if json is None else json
        if json is None:
            raise ValueError("No json provided.")
        return JsonGraph.json_to_graph(json)

    def convert_source_to_json(self, source: str | list) -> dict:
        """Converts a source file or list of source files to a json serializable object.

        Args:
        -----
            source (str): The source file to get the source files from, then convert to json. \n
            Or source (list): The list of source files to convert to json.

        Returns:
        --------
            dict: The json serializable object.
        """
        if source is None:
            raise ValueError("No source provided.")
        if isinstance(source, str):
            source = self.get_source_files(source)
        self.graph = self.parse_source(source)
        return self.convert_graph_to_json(self.graph)

    def load_json(self, json_file: str) -> dict:
        """Loads a json file into a json serializable object.

        Args:
        -----
            json_file (str): The json file to load.

        Returns:
        --------
            dict: The json serializable object.
        """
        return load_json_file(json_file)

    def save_json(self, json_file: str, data: dict):
        """Saves a json serializable object to a json file.

        Args:
        -----
            json_file (str): The json file to save the data to. \n
            data (dict): The json serializable object to save.
        """
        save_json_file(json_file, data)

    ########### SOURCE FILES ###############
    def get_source_files(self, source_file: str = None) -> list:
        """Gets all source files from a source file or directory.

        Args:
        -----
            source_file (str): The source file or directory to get the source files from.

        Returns:
        --------
            list: The list of source files.
        """
        _source_file: str = self.source[0] if source_file is None else source_file
        if _source_file is None:
            raise ValueError("No source provided.")
        return get_all_source_files(_source_file)

    ########### OUTPUT DIRECTORY ###########
    def set_output_dir(self, output_dir):
        """Sets the output directory for plots.

        Args:
        -----
            output_dir (str): The output directory to set.
        """
        self.plotter.set_plot_output_dir(output_dir)
        # TODO: does this need to be set in config for library?

    def reset_output_dir(self):
        """Resets the output directory for plots to default package output."""
        if self.plotter is None:
            self._set_plotter()
        self.plotter.reset_plot_output_dir()

    ########### PALETTE ####################
    def set_palette(self, palette_file_path):
        """Sets the palette for plots.

        Args:
        -----
            palette_file_path (str): The path to the palette.json file to set.
        """
        self.palette.load_palette(palette_file_path)

    def reset_palette(self):
        """Resets the palette to the default package palette."""
        self.palette.reset_palette()

    def export_palette_file(self, path: str) -> str:
        """Gets the palette.json file.

        Args:
        -----
            path (str): The path to export the palette.

        Returns:
        --------
            str: The palette file.
        """
        import os

        if not os.path.exists(path):
            raise ValueError(f"Path {path} does not exist.")
        return self.palette.export_palette(path)

    def get_palette_data(self):
        """Get the data of the current palette.

        Returns:
        --------
            dict: A dictionary containing the data of the current palette.
        """
        return self.palette.get_palette_data()

    def create_new_theme(
        self, node_type, base, label, shape, color, size, alpha
    ) -> dict:
        """Creates a new theme.

        Args:
        -----
            node_type (str): The node type to create a new theme for.
            base (str): The base color to use for the theme.
            label (str): The label color to use for the theme.
            shape (str): The shape color to use for the theme.
            color (str): The color to use for the theme.
            size (str): The size to use for the theme.
            alpha (str): The alpha to use for the theme.

        Returns:
        --------
            dict: The new theme.
        """
        return self.palette.create_new_theme(
            node_type, base, label, shape, color, size, alpha
        )

    ########### CONFIG ######################
    # def reset_config(self):
    #     Config.reset_config()

    ########### PROCESSOR ###################
    def run_process(
        self,
        source,
        _labels: bool = False,
        _json: bool = False,
        _grid: bool = False,
        _show: bool = False,
        _single_file: bool = False,
        _output_dir: str = None,
    ) -> dict:
        """Runs the process.

        Args:
        -----
            source (str): The source file or directory to get the source files from. \n
            _labels (bool): Whether to show the labels or not. \n
            _json (bool): Whether to save the json file or not. \n
            _grid (bool): Whether to show the grid or not. \n
            _show (bool): Whether to show the plot or not. (will interrupt the program until the plot is closed) \n
                RECOMMENDED TO KEEP '_show' FALSE. \n
            _single_file (bool): Whether to process a single file or the whole source file directory. \n
            _output_dir (str): The output directory to save the json file to.

        Returns:
        --------
            dict: The output directories for the json file and plots.
        """
        if _output_dir == "":
            if self.output_dir is not None and self.output_dir != "":
                _output_dir = self.output_dir

        processor = Processor(
            source, _labels, _json, _grid, _show, _single_file, _output_dir
        )
        return processor.main()


########################### NOTES ############################################

# Can use this class for simple use cases of the library
# Things like:
#   - Creating a graph from a source file
#   - Creating a graph from a json file
#   - Creating a plot from a networkx graph
#   - Creating a json file from a networkx graph
#   - Creating a custom theme for plots
#   - Getting full directory of source files
#   - Saving json data to a file
#   - Loading json data from a file
#   - Converting a networkx graph to a json object
#   - Converting a json object to a networkx graph
#   - Setting the output directory
#   - Getting the output directory
#   - Getting the default output directory
#   - Getting the default palette
#   - Getting the default config
#   - Resetting the config
#   - Resetting the palette
#   - Resetting the output directory

# these files need setters, getters, and resetters
#   - output_dir
#   - palette
#   - config
#   - source
#   - graph


# Work out some use cases for library use for low, mid, and adv users.
# 1. Create a graph from a source file, source directory (SourceParser)
# 2. Create a graph from a json file (JsonGraph)
# 3. Create a plot from a networkx graph, graph originating from json file, graph originating from source file/dir (Plotter)
# 4. Create a json file from a networkx graph, graph originating from json file, graph originating from source file/dir (JsonGraph)
# 5. Create a custom theme for plots (Palette)

# What are uses for directory functions?
# 1. Setting the output directory (set_output_dir), now this is for where graphs and jsons are saved
#       This is useful for the command line tool, but it doesn't seem like it would be desired to save the output for library use
#       During library use, it will return the object that was created
#       Could consider making this an internal function of the package _set_output_dir and remove import
#       TODO: also consider making a _cli_util.py to import the functions that are used by the cli tool only
#             ^^^ if the user really wants, they can import these functions themselves, but they are not needed for normal library use

# That's main functionality, but what about possible use cases for helper functions?
# 1. Getting full directory of source files (get_source_files)
#       Could also add a wrapper func in SourceParser that will call get_source_files to avoid pushing that function directly
# 2. Saving json data to a file (save_json_file), although this is really just a wrapper for json.dump
# 3. Loading json data from a file (load_json_file), although this is really just a wrapper for json.load
#       Could consider making these internal functions of the pacakage _save_json_file, _load_json_file and remove imports

# TODO: do we make a class CodeCarto that has all of these functions as methods as well for low level use?
#       ^^^ this would be a good way to keep the package organized and allow for low level use and still leave mid, adv use open
#       ^^^ this would also allow for the cli tool to be a wrapper for the CodeCarto class methods, would make it easier to maintain
#       ^^ call would be 'from codecarto import CodeCarto' and then 'cc = CodeCarto(INITIALIZE WITH ARGS)'
#       ^^ then call methods on the cc object, 'cc.create_graph_from_source_file()' < example
#       ^ consider Peter's useage of library in his project, would this be easier for him to use?

# This class would need all the low level functions
# 1. Create a graph from a source file, source directory (SourceParser)
# 2. Create a graph from a json file (JsonGraph)
# 3. Create a plot from a networkx graph, graph originating from json file, graph originating from source file/dir (Plotter)
# 4. Create a json file from a networkx graph, graph originating from json file, graph originating from source file/dir (JsonGraph)
# 5. Create a custom theme for plots (Palette)
# 6. Getting full directory of source files (get_source_files)
# 7. Saving json data to a file (save_json_file), although this is really just a wrapper for json.dump
# 8. Loading json data from a file (load_json_file), although this is really just a wrapper for json.load
