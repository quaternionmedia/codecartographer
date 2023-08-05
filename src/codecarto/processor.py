class Processor:
    """The code cartographer."""

    def __init__(
        self,
        file_path: str = __file__,
        do_json: bool = False,
        do_labels: bool = False,
        do_grid: bool = False,
        do_show: bool = False,
        do_single_file: bool = False,
        output_dir: str = "",
    ):
        """Initialize the CodeCartographer class.

        Parameters:
        -----------
        file_path (str) - Default: __file__
            The path to the file to be analyzed. \n
        do_json (bool) - Default: False
            Whether to create a json file of the graph. \n
        do_labels (bool) - Default: False
            Whether to label the nodes of the graph. \n
        do_grid (bool) - Default: False
            Whether to add a grid to the graph. \n
        do_show (bool) - Default: False
            Whether to show the graph. \n
        do_single_file (bool) - Default: False
            Whether to analyze a single file. \n
        output_dir (str) - Default: ""
            The path to the output directory. \n
        """
        from codecarto import Config

        print(f"\nCode Cartographer:\nProcessing File:\n{file_path}\n")

        self.file_path = file_path
        self.do_json = do_json
        self.do_labels = do_labels
        self.do_grid = do_grid
        self.do_show = do_show
        self.single_file = do_single_file
        self.config = Config()
        if output_dir and output_dir != "":
            self.config.set_config_property("output_dir", output_dir)

    def main(self) -> dict | None:
        """The main function of the code cartographer.

        Returns:
        --------
        dict | None
            The paths to the output directory.
                'version': the runtime version of the process. \n
                'output_dir': the path to the output directory. \n
                'version_dir': the path to the output/version directory. \n
                'graph_dir': the path to the output/graph directory. \n
                'graph_code_dir': the path to the output/graph/from_code directory. \n
                'graph_json_dir': the path to the output/graph/from_json directory. \n
                'json_dir': the path to the output/json directory. \n
                'json_graph_file_path': the path to the output/json/graph.json file.
        """
        from codecarto import Directories as Dir, Parser

        # Analyze the code
        _source_files: list[str] = []
        if self.single_file:
            _source_files = [self.file_path]
        else:
            _source_files = Dir.get_source_files(self.file_path)
        graph = Parser(
            source_files=_source_files,
        ).graph
        print("Visited Tree")

        # Process the graph
        if graph and graph.number_of_nodes() > 0:
            from codecarto import Directories as Dir, PolyGraph, Plotter

            # Create the output directory
            paths = Dir.new_output_directory(make_dir=True)

            # Create the graph plotter, needs to be same
            # plotter for both to handle seed correctly
            plotter: Plotter = Plotter(
                dirs=paths,
                file_path=self.file_path,
                do_labels=self.do_labels,
                do_grid=self.do_grid,
                do_show=self.do_show,
                do_single_file=self.single_file,
                do_ntx=True,
                do_custom=True,
            )

            # Plot the graph made from code
            print("Plotting Code Graph")
            plotter.plot(_graph=graph)
            print("Code Plots Saved\n")

            # Plot the graph made from json
            json_grapher: PolyGraph = PolyGraph(
                _path=paths["json_graph_file_path"],
                _graph=graph,
                _convert_back=self.do_json,
            )
            if self.do_json:
                print("Plotting JSON Graph")
                plotter.plot(
                    _graph=json_grapher.json_graph,
                    _json=True,
                )
                print("JSON Plots Saved\n")

            print("Finished\n")
            print(f"Output Directory:\n{paths['output_dir']}\n")
            return paths
        else:
            # No graph to plot
            print("No graph to plot")
            return None
