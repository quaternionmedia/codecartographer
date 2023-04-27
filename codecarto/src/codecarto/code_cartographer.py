from .themes.themes import Theme
from .code_parser import CodeParser
from .graph_plotter import GraphPlotter
from .json.json_converter import JsonConverter
from .utils.utils import set_up_directories


class CodeCartographer:
    """The code cartographer."""

    def __init__(self, file_path: str = __file__, args=None):
        """Initialize the CodeCartographer class.

        Parameters:
        -----------
        file_path : str
            The path to the file to parse.
        """
        print("\nCode Cartographer: ", file_path, "\n")
        Theme().__init__()
        self.file_path = file_path
        self.args = args
    
    def main(self):
        """The main function of the code cartographer."""
        # Analyze the code
        analyzer = CodeParser(self.file_path)
        print("Visited Tree")
        # Process the graph
        if analyzer.graph:
            # Get the iteration number and iteration directory
            directory_info = set_up_directories()
            print("Directories Made")
            # Plot the graph made from code
            GraphPlotter().plot(G=analyzer.graph, 
                              file_path=directory_info["code_graph_dir"])
            print("Code Plots Saved")
            # Save the graph as json
            json_converter = JsonConverter(
                analyzer.graph, directory_info["json_file_path"]
            )
            print("JSON Saved")
            # Plot the graph made from json
            GraphPlotter().plot(
                G=json_converter.json_graph, 
                file_path=directory_info["json_graph_dir"], 
                json=True
            )
            print("JSON Plots Saved")
        else:
            # No graph to plot
            print("No graph to plot")


# if __name__ == "__main__":
#     parse_args(sys.argv[1:])

########## OPTIONAL ##########

# if __name__ == "__main__":
#     CodeCartographer().main()

# from code_parser import CodeParser
# from graph_plotter import GraphPlotter
# from json_converter import JsonConverter
# from cli import parse_args

# class CodeCartographerApp:
#     def __init__(self):
#         self.theme = None
#         # ...

#     def read_input_file(self, file_path):
#         # Read input file and return its contents
#         pass

#     def analyze_code(self, code):
#         # Analyze the code and return the resulting graph
#         pass

#     def process_graph(self, graph):
#         # Process the graph and perform necessary operations (e.g., plotting, JSON conversion)
#         pass

#     def generate_output(self):
#         # Generate the final output (e.g., saving plots, JSON files)
#         pass

#     def run(self):
#         args = parse_args()

#         code = self.read_input_file(args.file_path)
#         graph = self.analyze_code(code)
#         self.process_graph(graph)
#         self.generate_output()

# if __name__ == "__main__":
#     app = CodeCartographerApp()
#     app.run()
