### codecarto\__init__.py

##############################################################################

"""A tool used to analyze and graph source code. \n

This package is used to analyze source code and create a graph of the \n
relationships between the various components of the code. The graph can be \n
saved as a json file and/or plotted as a graph image. \n

The package is designed to be used as a command line tool, but can also be \n
used as a library. \n

Classes:
--------
    JsonGraph - A class used to create a json representation of a graph. \n
        Notes: \n
            If an empty graph is passed to the class, the class will create a \n
            graph from the passed json file. \n

        Attributes: \n
            json_file_path:str - The path to the json file to load. \n
            json_data:dict - The json data loaded from the file. \n
            json_graph:networkx.DiGraph - A networkx graph object. \n

        Functions: \n
            save_json_data - A function used to save json data to a file. \n
            load_json_data - A function used to load json data from a file. \n
            graph_to_json - A function used to convert a networkx graph to a json object. \n
            json_to_graph - A function used to convert a json object to a networkx graph. \n

    Palette - A class used to create a color palette. \n
        Attributes: \n
            colors - A list of colors to use for the palette. \n

        Functions: \n
            get_color - A function used to get a color from the palette. \n
    SourceParser - A class used to parse source code. \n
    Processor - A class used to process source code. \n
    GraphPlot - A class used to plot a graph.
"""

##############################################################################
# Import the sub modules to make them easier to get at
from .config.config import Config
from .json.json_graph import JsonGraph
from .palette.palette import Palette
from .parser import SourceParser
from .processor import Processor
from .plotter import GraphPlot
from .json.json_utils import save_json_data as save_json, load_json_data as load_json
from .utils.directory.output_dir import set_output_dir
from .utils.directory.main_dir import MAIN_DIRECTORY
from .cli.cli import demo

##############################################################################
# Export the submodules.
__all__ = [
    "Config",
    "JsonGraph",
    "Palette",
    "SourceParser",
    "Processor",
    "GraphPlot",
    "save_json",
    "load_json",
    "set_output_dir",
    "demo",
]

### __init__.py ends here
