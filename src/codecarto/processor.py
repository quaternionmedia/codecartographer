class Processor: 
    """Runs through all parsing, plotting, json conversion, and outputting of the results."""

    def process(self,
                file_path: str = __file__,
                from_api: bool = False,
                do_single_file: bool = False,
                do_plot: bool = True,
                do_json: bool = False,
                do_labels: bool = False,
                do_grid: bool = False,
                do_show: bool = False,
                output_dir: str = "",) -> dict | None:
        """Parses the source code, creates a graph, creates a plot, creates a json file, and outputs the results.

        Parameters:
        -----------
        config (Config) - Default: None
            The code cartographer config object.
        file_path (str) - Default: __file__
            The path to the file to be analyzed.
        from_api (bool) - Default: False
            Whether the process is being run from the API.
        do_single_file (bool) - Default: False
            Whether to analyze a single file.
        do_plot (bool) - Default: True
            Whether to plot the graph.
        do_json (bool) - Default: False
            Whether to create a json file of the graph.
        do_labels (bool) - Default: False
            Whether to label the nodes of the graph.
        do_grid (bool) - Default: False
            Whether to add a grid to the graph.
        do_show (bool) - Default: False
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
        from codecarto import Directory as Dir, Parser

        # Set up the config and output directory
        if not from_api:
            self.print_status(f"\nCode Cartographer:\nProcessing File:\n{file_path}\n", from_api)
            from codecarto import Config
            config = Config()
            if output_dir and output_dir != "":
                config.set_config_property("output_dir", output_dir, from_api)

        # Analyze the code
        source_files: list[str] = []
        if do_single_file:
            source_files = [file_path]
        else:
            source_files = Dir.get_source_files(file_path)
        graph = Parser.parse_source_files(source_files)

        # Process the graph
        if graph and graph.number_of_nodes() > 0:
            from codecarto import Directory as Dir, PolyGraph, Plotter
 
            # TODO: until we figure out how to return a plot through API, we won't do this bit
            if not from_api:
                self.print_status("Visited Tree", from_api)

                # Create the output directory
                paths = Dir.create_output_dir(make_dir=True) 

                if do_plot:
                    # Create the graph plotter, needs to be same
                    # Plotter for both to handle seed correctly
                    plot: Plotter = Plotter()

                    # Set the plotter attributes
                    plot.set_plotter_attrs(dirs = paths,
                                        file_path = file_path,
                                        do_labels = do_labels,
                                        do_grid = do_grid,
                                        do_json = do_json,
                                        do_show = do_show,
                                        do_single_file = do_single_file,
                                        do_ntx = True,
                                        do_custom = True) 
                    
                    # Plot the graph made from code
                    self.print_status("Plotting Code Graph", from_api)
                    plot.plotter.plot(graph)
                    self.print_status("Code Plots Saved\n", from_api) 

                    # Create the json graph  
                    if do_json: # this is asking if we should convert back from json to graph 
                        # Create a json file of the graph  
                        json_graph = PolyGraph.graph_to_json_file_to_graph(graph, paths["json_graph_file_path"]) 

                        # Plot the graph from json file
                        self.print_status("Plotting JSON Graph", from_api)
                        plot.plotter.do_json = True
                        plot.plotter.plot(json_graph)
                        self.print_status("JSON Plots Saved\n", from_api)
                else:
                    from codecarto import Json
                    # Create a json file of the graph
                    PolyGraph.graph_to_json_data(graph)
                    Json.save_json(graph, paths["json_graph_file_path"])

                self.print_status("Finished\n")
                self.print_status(f"Output Directory:\n{paths['output_dir']}\n", from_api)
                return paths 
            else: 
                #TODO: this is just until we can figure out how to return a plot through API
                # this is being run through the API, don't create a bunch of stuff on server
                # just return the graph as json data
                return PolyGraph.graph_to_json_data(graph)
        else: 
            if not from_api:
                self.print_status("No graph to plot", from_api)
                return None
            else:
                from codecarto import ErrorHandler
                ErrorHandler.raise_error("Graph was not able to be created from file.")  

    def print_status(self, message:str = None, from_api: bool = False):
        """Print the status of the code cartographer.

        Parameters:
        -----------
        message (str) - Default: None
            The message to print. 
        """
        #TODO: this function is for local use until we can figure out how to return status messages through API
        if message and not from_api:
            print(message) 