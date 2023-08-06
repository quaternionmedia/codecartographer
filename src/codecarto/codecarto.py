""" CodeCarto: A Python library for code visualization. """

# This will pull all the package functionality to the top level which allows 
# for easier use of the package.
# The actual exporting of the functions happens in the top __init__.py file.
# Doing this here also allows for tying togethr multiple functions, as well
# as validating the data passed to the functions in a single place.

# API: API will call the functions from importing this file 
# and will be the only file that needs to be imported

# Lib: A local clone/fork/installation of the package will use 
# this file to call the functions from importing this file

# CLI: Using local CLI commands will call the functions from
# importing this file

# CLI-API: CLI commands can be used to call the API functions
# which in turn will reference the functions from this file

import os
import networkx as nx
from pydantic import BaseModel
from .config.config import Config
from .config.directory.main_dir import MAIN_DIRECTORY
from .config.directory.package_dir import CODE_CARTO_PACKAGE_VERSION
from .config.directory.palette_dir import PALETTE_DIRECTORY
from .config.directory.directories import print_all_directories
from .config.directory.import_source_dir import get_all_source_files
from .config.directory.output_dir import (
    get_output_dir,
    reset_output_dir,
    set_output_dir,
    new_output_directory,
    get_last_dated_dir,
)
from .models.graph_data import GraphData, get_graph_description
from .parser import Parser
from .plotter.palette import Palette
from .plotter.plotter import Plotter
from .plotter.positions import LayoutPositions 
from .polygraph.polygraph import PolyGraph 
from .processor import Processor
from .utils.utils import check_file_path, get_date_time_file_format, load_json_file, save_json_file
from .utils.errors import (ThemeError, 
                           ThemeCreationError, 
                           ThemeNotFoundError, 
                           ThemesDirNotFoundError, 
                           CliError, 
                           BaseNotFoundError, 
                           MissingParameterError)


class Theme(BaseModel):
    node_type: str
    base: str
    label: str
    shape: str
    color: str
    size: str
    alpha: str


class ParserHandler: 
    def __init__(self):
        self.parser: Parser = Parser()
        
    def parse_source_files(self, source: str | list = None) -> nx.DiGraph:
        """Parses a source file or list of source files into a networkx graph.

        Args:
        -----
            source (str): The source file to get the source files from, then parse. \n
            Or source (list): The list of source files to parse.

        Returns:
        --------
            nx.DiGraph: The networkx graph.
        """ 
        if source is None:
            ErrorHandler.raise_error("No source provided.")
        if isinstance(source, str):
            source = DirectoryHandler.get_source_files(source)
        parser: Parser = Parser(source) 
        return parser.graph


class PlotterHandler:
    def __init__(self):
        self.plotter: Plotter = Plotter()

    def set_plotter_attrs(self,
                          dirs: dict[str, str] = None,
                          file_path: str = "",
                          do_labels: bool = False,
                          do_grid: bool = False,
                          do_json: bool = False,
                          do_show: bool = False,
                          do_single_file: bool = False,
                          do_ntx: bool = True,
                          do_custom: bool = True): 
        """Sets the plotter attributes.

        Parameters:
        -----------
            dirs (dict): 
                The directories to use for the plotter.
            file_path (str): 
                The file path to use for the plotter.
            do_labels (bool): 
                Whether or not to show the labels.
            do_grid (bool): 
                Whether or not to show the grid.
            do_json (bool):
                Whether or not to save the json file.
            do_show (bool): 
                Whether or not to show the plot.
            do_single_file (bool): 
                Whether or not to save the plot to a single file.
            do_ntx (bool): 
                Whether or not to save the plot to a networkx file.
            do_custom (bool): 
                Whether or not to save the plot to a custom file.
        """
        self.plotter.dirs = dirs if dirs is not None else self.plotter.dirs
        self.plotter.file_path = file_path if file_path is not None else self.plotter.file_path
        self.plotter.do_labels = do_labels
        self.plotter.do_grid = do_grid
        self.plotter.do_json = do_json
        self.plotter.do_show = do_show
        self.plotter.do_single_file = do_single_file
        self.plotter.do_ntx = do_ntx
        self.plotter.do_custom = do_custom

    def plot_graph(self, 
                   graph: GraphData, 
                   output_dir: str = None, 
                   file_name: str = None, 
                   specific_layout: str = "", 
                   do_grid: bool = False, 
                   do_json: bool = False,
                   api: bool = False, 
                   )-> dict[dict, str]:
        """Plots a graph representing code.

        Parameters:
        -----------
            graph (GraphData):  
                The networkx graph to plot. 
            output_dir (str): 
                The directory to save the plot to.
            file_name (str): 
                The name of the plot file.
            specific_layout (str):
                The specific layout to use for the plot. 
                    default (""): will plot all layouts.
            do_grid (bool):
                Whether or not to show the grid.
            do_json (bool):
                Whether or not to save the json file.
            api (bool):
                Whether or not the function is being called from the API.

        Returns:
        --------
            dict:  
                The Json data and output directory. 
        """

        # Validate the data
        if graph is None:
            ErrorHandler.raise_error("No graph provided.") 
        if not api and output_dir is None:
            output_dir = get_output_dir()
        if file_name is None:
            file_name = f"GraphPlot {get_date_time_file_format()}" 

        # Convert the GraphData object to a networkx graph
        graph = PolyGraph.graphdata_to_nx(GraphData)

        # Set the plotter parameters
        self.plotter.dirs["output_dir"] = output_dir
        self.plotter.do_grid = do_grid
        self.plotter.do_json = do_json

        # Plot the graph
        self.plotter.plot(graph, specific_layout)

        # Get the last dated folder in output folder 
        last_date_folder = DirectoryHandler.get_last_dated_dir()

        # Get the json object 
        json_file_path = last_date_folder + "/json/graph_data.json"
        json_data:dict = JsonHandler.load_json(json_file_path)

        # Return the json object and output directory of the plots
        return {"graph_data":json_data, "output_dir":self.plotter.dirs["output_dir"]}
    
    def set_plot_output_dir(self, output_dir: str = None):
        """Sets the plot output directory.

        Parameters:
        -----------
            output_dir (str) Default = None:
                The directory to use.
        """ 

        # Validate the data
        if output_dir is None:
            ErrorHandler.raise_error("No output directory provided.")
        if not os.path.isdir(output_dir):
            ErrorHandler.raise_error("The provided output directory does not exist.") 
        if not output_dir == self.plotter.dirs["output_dir"]: 
            # Set the plot output directory
            self.plotter.dirs["output_dir"] = output_dir
            self.plotter.dirs["graph_code_dir"] = os.path.join(output_dir, "code")
            self.plotter.dirs["graph_json_dir"] = os.path.join(output_dir, "json")
        else:
            ErrorHandler.raise_error("The provided output directory is already set as the plot output directory.")

    def reset_plot_output_dir(self):
        """Resets the plot output directory to the default output directory."""
        from codecarto import Directory as Dir

        self.plotter.dirs = Dir.reset_output_dir(make_dir=True)


class ModelHandler:
    def get_graph_description() -> dict:
        """Gets the graph description.

        Returns:
        --------
            dict: The graph description.
        """
        return get_graph_description()


class PolyGraphHandler:  
    def __init__(self):
        """Converts an assortment of data objects to an nx.DiGraph object and vice versa."""
        self.polygraph: PolyGraph = PolyGraph() 

    def graph_to_json_file_to_graph(self, graph: nx.DiGraph, json_file_path: str) -> nx.DiGraph:
        """Converts a networkx graph to a json file and then back to a networkx graph from the json file.\n
        This is used to ensure that the json file is valid and can be converted back to a networkx graph.

        Parameters:
        -----------
            graph (networkx.classes.graph.Graph):
                The networkx graph to convert to json data.
            json_file_path (str):
                The path to save the json data to.

        Returns:
        --------
            networkx.classes.graph.Graph: The networkx graph generated from the saved json data.
        """

        # Validate the data
        if graph is None:
            ErrorHandler.raise_error("No graph provided.")
        if json_file_path is None:
            ErrorHandler.raise_error("No json file path provided.")

        # Convert the networkx graph to a json data and save it to a json file
        json_data:dict = self.graph_to_json_data(graph)
        JsonHandler.save_json(json_file_path, json_data)

        # Convert the json file back to a networkx graph 
        return self.json_file_to_graph(json_file_path)

    def json_file_to_graph(self, json_file_path: str) -> nx.DiGraph:
        """Converts a json file to a networkx graph.

        Parameters:
        -----------
            json_file_path (str):
                The path to the json file to convert to a networkx graph.

        Returns:
        --------
            networkx.classes.graph.Graph: The networkx graph.
        """

        # Validate the data
        if json_file_path is None:
            ErrorHandler.raise_error("No json file path provided.")
        if not os.path.isfile(json_file_path):
            ErrorHandler.raise_error("The provided json file path does not exist.")
 
        # Convert the json data to a networkx graph 
        return self.json_data_to_graph(JsonHandler.load_json(json_file_path))    

    def graph_to_json_data(self, graph: nx.DiGraph) -> dict:
        """Converts a networkx graph to a json object.

        Parameters:
        -----------
            graph (networkx.classes.graph.Graph):
                The graph to convert to json.

        Returns:
        --------
            dict: The json object.
        """

        # Validate the data
        if graph is None:
            ErrorHandler.raise_error("No graph provided.")
        
        return self.polygraph.graph_to_json_data(graph)
    
    def json_data_to_graph(self, json_data: dict) -> nx.DiGraph:
        """Converts a json object to a networkx graph.

        Parameters:
        -----------
            json_data (dict):
                The json object to convert to a networkx graph.

        Returns:
        --------
            networkx.classes.graph.Graph: The networkx graph.
        """

        # Validate the data
        if json_data is None:
            ErrorHandler.raise_error("No json data provided.")

        return self.polygraph.json_data_to_graph(json_data)

    def source_code_to_json_data(self, source: str | list) -> dict:
        """Converts a source file or list of source files to a json serializable object.

        Parameters:
        -----------
            source (str): 
                The source file to get the source files from, then convert to json. \n
            OR source (list): 
                The list of source files to convert to json.

        Returns:
        --------
            dict: The json serializable object.
        """
        if source is None:
            raise ErrorHandler.raise_error("No source file path provided.")
        if isinstance(source, str):
            source = DirectoryHandler.get_source_files(source)
        if isinstance(source, list):
            graph = Parser.parse_code(source) 
            return self.polygraph.graph_to_json_data(graph)
        else:
            raise ErrorHandler.raise_error("'source' must be a file path or list of file paths.")


class PaletteHandler:
    def __init__(self):
        self.palette = Palette()

    def get_palette(self):
        """Get the data of the current palette.

        Returns:
        --------
            dict: A dictionary containing the data of the current palette.
        """
        return self.palette.get_palette_data()

    def set_palette(self, palette_file_path: str):
        """Sets the palette for plots.

        Args:
        -----
            palette_file_path (str): The path to the palette.json file to set.
        """
        self.palette.load_palette(palette_file_path)

    def reset_palette(self):
        """Resets the palette to the default package palette."""
        self.palette.reset_palette()

    def export_palette(self, path: str) -> str:
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
            ErrorHandler.raise_error(f"Path {path} does not exist.")
        return self.palette.export_palette(path)
    
    def import_palette(self, path: str):
        """Imports a palette.json file.

        Args:
        -----
            path (str): The path to import the palette from.
        """
        import os

        if not os.path.exists(path):
            ErrorHandler.raise_error(f"Path {path} does not exist.")
        self.palette.import_palette(path)

    def create_new_theme(self, theme: Theme) -> dict:
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
            theme.node_type,
            theme.base,
            theme.label,
            theme.shape,
            theme.color,
            theme.size,
            theme.alpha,
        )


class PositionHandler:
    def __init__(self, include_networkx: bool = True, include_custom: bool = True):
        self.layouts = LayoutPositions(include_networkx, include_custom)

    def add_layout(self, name: str, function: callable, attributes: list):
        """Adds a layout to the list of available layouts.

        Args:
        -----
            name (str): The name of the layout to add. \n
            function (callable): The function to use for the layout. \n
            attributes (list): The attributes to use for the layout.
        """
        self.layouts.add_layout(name, function, attributes)

    def add_networkx_layouts(self):
        """Adds all networkx layouts to the list of available layouts."""
        self.layouts.add_networkx_layouts()

    def add_custom_layouts(self):
        """Adds all custom layouts to the list of available layouts."""
        self.layouts.add_custom_layouts()

    def get_layout_names(self) -> list:
        """Gets all layout names from the list of available layouts.

        Returns:
        --------
            list: The name of available layouts.
        """
        return self.layouts.get_layout_names()

    def get_positions(self, graph: nx.DiGraph, layout: str = "") -> dict:
        """Gets the positions of the nodes in the graph.

        Args:
        -----
            graph (nx.DiGraph): The networkx graph to get the positions of. \n
            layout (str): The layout to use to get the positions of the nodes.

        Returns:
        --------
            dict: The positions of the nodes in the graph.
        """
        return self.layouts.get_positions(graph, layout)

    def get_layouts(self) -> list:
        """Gets the available layouts.

        Returns:
        --------
            list: The available layouts.
        """
        return self.layouts.get_layouts()

    def get_layout(self, name: str) -> tuple:
        """Gets a layout from the list of available layouts.

        Args:
        -----
            name (str): The name of the layout to get.

        Returns:
        --------
            tuple: The layout.
        """
        return self.layouts.get_layout(name)


class ProcessorHandler: 
    def process(
        self,
        source: str,
        api: bool = False,
        plot: bool = True,
        labels: bool = False,
        json: bool = False,
        grid: bool = False,
        show: bool = False,
        single_file: bool = False,
        output_dir: str = None,
        ) -> dict:
        """Parses the source code, creates a graph, creates a plot, creates a json file, and outputs the results.

        Parameters:
        -----------
        source (str): 
            The source directory or source file to process. 
        api (bool):
            Whether calling from api or not.
        single_file (bool): 
            Whether to process a single file or the whole source file directory. 
        plot (bool):
            Whether to plot the graph or not.
        labels (bool): 
            Whether to show the labels or not.  
        json (bool): 
            Whether to save the json file or not.  
        grid (bool): 
            Whether to show the grid or not. 
        show (bool): 
            Whether to show the plot or not. (will interrupt the program until the plot is closed) 
                RECOMMENDED TO KEEP '_show' FALSE.  
        output_dir (str): 
            The output directory to save the json file to.

        Returns:
        --------
        dict | None
            If called from the API dict is json object of the graph.\n
            If called locally dict is the paths to the output directory.
                'version': 
                    the runtime version of the process. 
                'output_dir': 
                    the path to the output directory. 
                'version_dir': 
                    the path to the output/version directory.  
                'graph_dir': 
                    the path to the output/graph directory. 
                'graph_code_dir': 
                    the path to the output/graph/from_code directory. 
                'graph_json_dir': 
                    the path to the output/graph/from_json directory. 
                'json_dir': 
                    the path to the output/json directory.  
                'json_graph_file_path': 
                    the path to the output/json/graph.json file.
        """ 
        
        # Validate the source
        if not os.path.exists(source):
            ErrorHandler.raise_error(f"Source {source} does not exist.")
        if not os.path.isdir(source) and not os.path.isfile(source):
            ErrorHandler.raise_error(f"Source {source} is not a directory or file.")

        if not api:
            return Processor.process(source, api, plot, labels, json, grid, show, single_file, output_dir) 
        else:
            return Processor.process(source=source, api=api, single_file=single_file)


class DirectoryHandler:
    def __init__(self, source_files: list = None):
        self.source: list = source_files
        self.parser = None
        self.graph = None

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
            ErrorHandler.raise_error("No source provided.")
        return get_all_source_files(_source_file)

    def get_output_dir(self) -> str:
        """Gets the output directory.

        Returns:
        --------
            str: The output directory.
        """
        return get_output_dir()

    def reset_output_dir(self) -> str:
        """Resets the output directory to the default package output."""
        return reset_output_dir()

    def set_output_dir(self, output_dir: str) -> str:
        """Sets the output directory.

        Args:
        -----
            output_dir (str): The output directory to set.
        """
        return set_output_dir(output_dir)

    def create_output_dir(self, make_dir: bool = False) -> str:
        """Setup the output directory.

        Parameters:
        -----------
        make_dir : bool
            Whether or not to make the output directory. If False, the output directory is set to 'RUN_TIME' filler string.

        Returns:
        --------
        str
            The path to the output directory.
        """
        return reset_output_dir(make_dir)
    
    def get_last_dated_dir() -> str:
        """Gets the last dated folder.

        Returns:
        --------
            str: The last dated folder.
        """
        return get_last_dated_dir()
    
    def get_main_dir(self) -> str:
        """Gets the main directory.

        Returns:
        --------
            str: The main directory.
        """
        return MAIN_DIRECTORY

    def get_package_version(self) -> str:
        """Gets the package version.

        Returns:
        --------
            str: The package version.
        """
        return CODE_CARTO_PACKAGE_VERSION

    def get_palette_directory(self):
        """Gets the palette directory.

        Returns:
        --------
            str: The palette directory.
        """
        return PALETTE_DIRECTORY

    def print_all_directories(self) -> dict:
        """Prints all directories."""
        return print_all_directories()


class JsonHandler:
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


class UtilityHandler:
    def __init__(self):
        self.utility = None

    def get_date_time_file_format(self) -> str:
        """Gets the date time file format.

        Returns:
        --------
            str: The date time file format.
        """
        return get_date_time_file_format()
    
    def check_file_exists(self, file: str) -> bool:
        """Checks if a file exists.

        Args:
        -----
            file (str): The file to check.

        Returns:
        --------
            bool: Whether the file exists or not.
        """
        return check_file_path(file)


class LogHandler: 
    from datetime import datetime

    def __init__(self):
        self.log_handler = None

    def log_duration(self, path:str = None, start:datetime = None, end:datetime=None, duration:float=None) -> None:
        """Logs process duration.

        Parameters:
        -----------
            path (str): 
                The API router path.
            start (datetime): 
                The start time of the process.
            end (datetime): 
                The end time of the process.
            duration (float): 
                The duration of the process.
        """
        if path is None:
            ErrorHandler.raise_error("No path provided.")
        if start is None:
            ErrorHandler.raise_error("No start time provided.")
        if end is None:
            ErrorHandler.raise_error("No end time provided.")
        if duration is None:
            ErrorHandler.raise_error("No duration provided.")

        #TODO: Move this to a Logging sub module
        # connect to the database 
        # insert error into ErrorLog table in database
        pass


class ErrorHandler: 
    class Error(BaseModel):
        exception: Exception = None
        caller: str = None
        break_line: int = -1
        message: str = None

        def __init__(self, exception: Exception, caller: str = None, break_line: int = -1, message: str = None):
            self.exception = exception
            self.caller = caller
            self.break_line = break_line
            self.message = message

    def __init__(self):
        self.error_handler = None 
        self.ThemeError = ThemeError
        self.ThemeCreationError = ThemeCreationError
        self.ThemeNotFoundError = ThemeNotFoundError
        self.ThemesDirNotFoundError = ThemesDirNotFoundError
        self.CliError = CliError
        self.BaseNotFoundError = BaseNotFoundError
        self.MissingParameterError = MissingParameterError
        

    def raise_error(self, error: str) -> None:
        """Raises an error.

        Parameters:
        -----------
            error (str): The error to raise.
        """

        #TODO: Adapt this to be codecarto custom instead of just random raised error
        raise ValueError(error)
    
    def log(self, exception: Exception = None, caller: str = None, break_line: int = -1, message: str = None) -> None:
        """Logs an exception.

        Parameters:
        -----------
            exception (Exception): 
                The exception to log.
            caller (str): 
                The caller of the exception.
            break_line (int): 
                The line code broke at.
            message (str): 
                The message to log.
        """

        #TODO: Move this to an Error sub module
        # Construct Error Log object and log the error
        error_obj = self.Error(exception=exception, caller=caller, break_line=break_line, message=message)
        self.log_error(error_obj)

    def log_error(self, error: Error) -> None:
        """Logs an error.

        Parameters:
        -----------
            error (Error): The error to log.
        """

        #TODO: Move this to an Error sub module
        # connect to the database 
        # insert error into ErrorLog table in database
        pass
      
########################### NOTES ############################################

# Example use for imported library
# import CodeCarto
# cc = CodeCarto()
# cc.set_output_dir("path/to/output/dir")

# For FastAPI use, functions will be in individual routes
# import, export, config, and convert routes

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
# 1. Create a graph from a source file, source directory (Parser)
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
#       Could also add a wrapper func in Parser that will call get_source_files to avoid pushing that function directly
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
# 1. Create a graph from a source file, source directory (Parser)
# 2. Create a graph from a json file (JsonGraph)
# 3. Create a plot from a networkx graph, graph originating from json file, graph originating from source file/dir (Plotter)
# 4. Create a json file from a networkx graph, graph originating from json file, graph originating from source file/dir (JsonGraph)
# 5. Create a custom theme for plots (Palette)
# 6. Getting full directory of source files (get_source_files)
# 7. Saving json data to a file (save_json_file), although this is really just a wrapper for json.dump
# 8. Loading json data from a file (load_json_file), although this is really just a wrapper for json.load
