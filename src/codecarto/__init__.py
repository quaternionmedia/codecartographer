### codecarto\__init__.py
##############################################################################
# TODO: extend these docstrings with new classes
##############################################################################
"""A tool used to analyze and graph source code. \n

This package is used to analyze source code and create a graph of the \n
relationships between the various components of the code. The graph can be \n
saved as a json file and/or plotted as a graph image. \n

The package is designed to be used as a command line tool, but can also be \n
used as a library. \n

Classes:
--------
    PolyGraph - A class used to create a json representation of a graph. \n
        Functions: \n
            graph_to_json_file - A function used to convert a networkx graph to a json object. \n
            json_file_to_graph - A function used to convert a json object to a networkx graph. \n
            graph_to_json_data - A function used to convert a networkx graph to a json object. \n
            json_data_to_graph - A function used to convert a json object to a networkx graph. \n
            graphdata_to_nx - A function used to convert a GraphData object to a networkx graph. \n
            
    Palette - A class used to create a color palette. \n
        Attributes: \n
            colors - A list of colors to use for the palette. \n

        Functions: \n
            get_color - A function used to get a color from the palette. \n
    Parser - A class used to parse source code. \n
    Processor - A class used to process source code. \n
    Plotter - A class used to plot a graph.
"""

from .config.config_process import initiate_package

initiate_package()

########################### IMPORTS #######################################
# # Import the sub modules to make them easier to get at
# from .codecarto import (
#     Config,
#     DirectoryHandler as Directory,
#     GraphData,
#     LogHandler,
#     ModelHandler as Model,
#     PaletteHandler as Palette,
#     ParserHandler as Parser,
#     PlotterHandler as Plotter,
#     PolyGraphHandler as PolyGraph,
#     PositionHandler as Position,
#     ProcessorHandler as Processor,
#     Theme,
#     UtilityHandler as Utility,
#     save_json,
#     load_json,
# )


# ########################### EXPORTS #########################################
# # Export the submodules.
# __all__ = [
#     "Config",
#     "Directory",
#     "GraphData",
#     "Json",
#     "LogHandler",
#     "Model",
#     "Palette",
#     "Parser",
#     "Plotter",
#     "PolyGraph",
#     "Position",
#     "Processor",
#     "Theme",
#     "Utility",
# ]

# ########################### LOGGER ##########################################
# import logging

# # create logger with 'codecarto'
# logger = logging.getLogger("codecarto")
# logger.setLevel(logging.DEBUG)  # set root logger level

# # logging log levels
# # CRITICAL = 50
# # FATAL = CRITICAL
# # ERROR = 40
# # WARNING = 30
# # WARN = WARNING
# # INFO = 20
# # DEBUG = 10
# # NOTSET = 0

# # create console handler with a higher log level
# ch = logging.StreamHandler()
# ch.setLevel(logging.INFO)  # set handler level

# # create formatter and add it to the handlers
# formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# ch.setFormatter(formatter)

# # add the handlers to the logger
# logger.addHandler(ch)

# # can use logger instance in your code, like this:
# # logger.debug("This is a debug message.")
# # logger.info("This is an informational message.")
# # logger.warning("This is a warning message.")
# # logger.error("This is an error message.")
# # logger.critical("This is a critical message.")

# # create file handler which logs even debug messages
# fh = logging.FileHandler("codecarto.log")
# fh.setLevel(logging.DEBUG)
# fh.setFormatter(formatter)
# logger.addHandler(fh)


##############################################################################
### __init__.py ends here
