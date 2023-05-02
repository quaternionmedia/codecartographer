class Processor:
    """The code cartographer."""

    def __init__(self, file_path: str = __file__, args=None):
        """Initialize the CodeCartographer class.

        Parameters:
        -----------
        file_path : str
            The path to the file to parse.
        """
        print("\nCode Cartographer: ", file_path, "\n")

        self.file_path = file_path
        self.args = args

    def main(self):
        """The main function of the code cartographer."""
        from .utils.directory.import_source_dir import get_all_source_files
        from .test import SourceParser

        # Analyze the code
        graph = SourceParser(
            source_files=get_all_source_files(self.file_path),
        ).graph
        print("Visited Tree")

        # Process the graph
        if graph:
            from .utils.directory.output_dir import setup_output_directory
            from .json.json_graph import JsonGraph
            from .plotter import GraphPlot

            # Create the output directory
            paths = setup_output_directory(make_dir=True)

            # Create the graph plotter, needs to be same
            # plotter for both to handle seed correctly
            plotter: GraphPlot = GraphPlot(_dirs=paths)

            # Plot the graph made from code
            print("\nPlot Code Graph")
            plotter.plot(_graph=graph)
            print("Code Plots Saved")

            # Plot the graph made from json
            print("\nPlot JSON Graph")
            json_grapher: JsonGraph = JsonGraph(
                _path=paths["json_graph_file_path"], _graph=graph
            )
            plotter.plot(
                _graph=json_grapher.json_graph,
                json=True,
            )
            print("JSON Plots Saved\n")
        else:
            # No graph to plot
            print("No graph to plot")
