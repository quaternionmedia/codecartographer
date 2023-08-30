
previous_output_dir: str = ""

def process(
    file_path: str = __file__,
    from_api: bool = False,
    single_file: bool = False,
    plot: bool = True,
    json: bool = False,
    labels: bool = False,
    grid: bool = False,
    show_plot: bool = False,
    output_dir: str = "",
) -> dict | None:
    """Parses the source code, creates a graph, creates a plot, creates a json file, and outputs the results.

    Parameters:
    -----------
    config (Config) - Default: None
        The code cartographer config object.
    file_path (str) - Default: __file__
        The path to the file to be analyzed.
    from_api (bool) - Default: False
        Whether the process is being run from the API.
    single_file (bool) - Default: False
        Whether to analyze a single file.
    plot (bool) - Default: True
        Whether to plot the graph.
    json (bool) - Default: False
        Whether to create a json file of the graph.
    labels (bool) - Default: False
        Whether to label the nodes of the graph.
    grid (bool) - Default: False
        Whether to add a grid to the graph.
    show_plot (bool) - Default: False
        Whether to show the graph.
    output_dir (str) - Default: ""
        The path to the output directory.

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
    from .parser.parser import Parser
    from .parser.import_source_dir import get_all_source_files
    from .config.config_process import get_config_data
    config_data: dict = get_config_data()
    config_path: str = config_data["config_path"]

    #TODO: Should we do a progress bar for all of these??
    # If we do, we'll need to calculate the 

    ############# SETUP OUTPUT #############
    if not from_api:
        print_status(
            f"\nCodeCartographer:\nProcessing File:\n{file_path}", from_api
        )
        # if the user provides an output directory, use it instead of the one in the config
        # BE SURE TO CHANGE THE OUTPUT DIRECTORY IN THE CONFIG FILE BACK TO THE PREVIOUS ONE
        if output_dir and output_dir != "":
            previous_output_dir: str = config_data["output_dir"]
            config_data["output_dir"] = output_dir
            save_json(config_data, config_path)

    ############# PARSE THE CODE #############
    source_files: list[str] = []
    if single_file:
        source_files = [file_path]
    else:
        source_files = get_all_source_files(file_path)
    graph = Parser(source_files=source_files).graph
    parse_msg: str = f"... {len(source_files)} source files parsed ...\n"
    print_status(parse_msg, from_api)

    ############# PROCESS THE GRAPH #############
    return_data:dict = None
    if graph and graph.number_of_nodes() > 0:
        from .plotter.plotter import Plotter
        from .polygraph.polygraph import PolyGraph
        from .config.directory.output_dir import create_output_dirs

        # TODO: until we figure out how to return a plot through API, 
        # we won't do the plotting we'll just return the json file of the graph
        pg: PolyGraph = PolyGraph()
        if not from_api:
            # Create the output directory
            paths = create_output_dirs()

            # Plot the graph
            if plot:
                # Create the graph plotter, needs to be same
                # Plotter for both to handle seed correctly
                plot: Plotter = Plotter()

                # Set the plotter attributes
                plot.set_plotter_attrs(
                    dirs=paths,
                    file_path=file_path,
                    labels=labels,
                    grid=grid,
                    json=False,
                    show_plot=show_plot,
                    single_file=single_file,
                    ntx_layouts=True,
                    custom_layouts=True,
                )

                # Plot the graph made from code
                print_process_settings(plot, from_api)
                print_status("", from_api)
                if grid:
                    print_status("Plotting all layouts to a grid...", from_api)
                else:
                    print_status("Plotting all layouts in separate files...", from_api)
                print_status("Plotting Source Code Graph...\n", from_api)
                plot.plot(graph)
                print_status("Source Code Plots Saved...\n", from_api)
                
                # Create a json file of the graph
                print_status("Converting Graph to JSON...", from_api)
                json_graph_file = paths["json_file_path"]
                pg.graph_to_json_file(graph, json_graph_file)

                # Create the json graph
                if json:  # this is asking if we should convert back from json to graph
                    print_status("Converting JSON back to Graph...", from_api)
                    json_graph = pg.json_file_to_graph(json_graph_file)

                    # Plot the graph from json file
                    plot.json = True
                    if grid:
                        print_status("Plotting all layouts to a grid...", from_api)
                    else:
                        print_status("Plotting all layouts in separate files...", from_api)
                    print_status("Plotting JSON Graph...\n", from_api)
                    plot.plot(json_graph)
                    print_status("JSON Plots Saved...\n", from_api)
            else:
                from .utils.utils import save_json

                # Create a json file of the graph
                pg.graph_to_json_data(graph)
                save_json(graph, paths["json_file_path"])

            print_status("\nFinished!\n")
            print_status(
                f"Output Directory:\n{paths['output_dir']}\n", from_api
            )
            return_data = paths
        else:
            # TODO: this is just until we can figure out how to return a plot through API
            # this is being run through the API, don't create a bunch of stuff on server
            # just return the graph as json data
            return_data = pg.graph_to_json_data(graph)
    else:
        if not from_api:
            print_status("No graph to plot\n", from_api)
            return_data = None
        else:
            raise ValueError("Graph was not able to be created from file.")

    # Change the output dir back to the previous one 
    if not from_api: # not needed for API
        # BE SURE TO CHANGE THE OUTPUT DIRECTORY IN THE CONFIG FILE BACK TO THE PREVIOUS ONE
        if output_dir and output_dir != "" and previous_output_dir != "":
            config_data["output_dir"] = previous_output_dir
            save_json(config_data, config_path)

    return return_data

def print_status(message: str = None, from_api: bool = False):
    """Print the status of the code cartographer.

    Parameters:
    -----------
    message (str) - Default: None
        The message to print.
    """
    # TODO: this function is for local use until we can figure out how to return status messages through API
    if message and not from_api:
        print(message)

def print_process_settings(plotter, from_api: bool = False):
    """Print the settings for the process."""
    from .plotter.plotter import Plotter
    plot: Plotter = plotter
    settings_msg:str = f"Plot Settings:\n"
    settings_msg += f"    Labels: {plot.labels}\n"
    settings_msg += f"    Grid: {plot.grid}\n"
    settings_msg += f"    JSON: {plot.json}\n"
    settings_msg += f"    Show Plot: {plot.show_plot}\n"
    settings_msg += f"    Single File: {plot.single_file}\n"
    settings_msg += f"    NTX Layouts: {plot.ntx_layouts}\n"
    settings_msg += f"    Custom Layouts: {plot.custom_layouts}\n"
    print_status(settings_msg, from_api)
