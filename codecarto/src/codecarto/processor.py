class Processor:
    """The code cartographer."""

    def __init__(
        self,
        file_path: str = __file__,
        do_json: bool = False,
        do_labels: bool = False,
        do_grid: bool = False,
        do_show: bool = False,
    ):
        """Initialize the CodeCartographer class.

        Parameters:
        -----------
        file_path : str
            The path to the file to parse.
        """
        print(f"\nCode Cartographer:\nProcessing File:\n{file_path}\n")

        self.file_path = file_path
        self.do_json = do_json
        self.do_labels = do_labels
        self.do_grid = do_grid
        self.do_show = do_show

    def main(self) -> dict | None:
        """The main function of the code cartographer.

        Returns:
        --------
        dict | None
            The dictionary of the graph data or None if no graph.
        """
        from .utils.directory.import_source_dir import get_all_source_files
        from .parser import SourceParser

        # Analyze the code
        graph = SourceParser(
            source_files=get_all_source_files(self.file_path),
        ).graph
        print("Visited Tree")

        # Process the graph
        if graph and graph.number_of_nodes() > 0:
            from .utils.directory.output_dir import setup_output_directory
            from .json.json_graph import JsonGraph
            from .plotter import GraphPlot

            # Create the output directory
            paths = setup_output_directory(make_dir=True)

            # Create the graph plotter, needs to be same
            # plotter for both to handle seed correctly
            plotter: GraphPlot = GraphPlot(
                _dirs=paths,
                do_labels=self.do_labels,
                do_grid=self.do_grid,
                do_show=self.do_show,
            )

            # Plot the graph made from code
            print("Plotting Code Graph")
            plotter.plot(_graph=graph)
            print("Code Plots Saved\n")

            # Plot the graph made from json
            json_grapher: JsonGraph = JsonGraph(
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
