import tempfile
from pathlib import Path

from ..src.codecarto.parser import SourceParser
from ..src.codecarto.utils.directory.output_dir import set_output_dir


def test_parser():
    """Test SourceParser class functions and output graph."""
    try:
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)

            # Create sample project files
            main_file_path = temp_dir_path / "main.py"
            scramble_file_path = temp_dir_path / "scramble.py"
            print_file_path = temp_dir_path / "print.py"

            # Write sample code to the files
            with open(main_file_path, "w") as main_file:
                main_file.write(
                    "from scramble import Scrambler\nfrom print import Printer\n\ninput_str = 'Hello, World!'\nscrambler = Scrambler()\nprinter = Printer()\n\nscrambled_str = scrambler.scramble(input_str)\nprinter.print(scrambled_str)"
                )

            with open(scramble_file_path, "w") as scramble_file:
                scramble_file.write(
                    "import random\n\nclass Scrambler:\n    def scramble(self, s: str) -> str:\n        chars = list(s)\n        random.shuffle(chars)\n        return ''.join(chars)"
                )

            with open(print_file_path, "w") as print_file:
                print_file.write(
                    "class Printer:\n    def print(self, s: str):\n        print(s)"
                )

            # send files in a list to parser
            source_files = [str(main_file_path), str(scramble_file_path), str(print_file_path)]
            parser = SourceParser(source_files)

            # get back parser's graph
            graph = parser.graph

            # check if the output graph is correct
            # TODO: extend this to the other ast elements of test code
            # be sure to check SourceParser for which visitors add nodes
            # check nodes
            assert len(graph.nodes) > 0
            assert len(graph.nodes) == 7
            assert graph.number_of_nodes() == 7
            assert graph.has_node("main.py")
            assert graph.has_node("scramble.py")
            assert graph.has_node("print.py")
            assert graph.has_node("Scrambler")
            assert graph.has_node("Printer")
            assert graph.has_node("scramble")
            assert graph.has_node("print")
            # check node attributes
            assert graph.nodes["main.py"]["type"] == "module"
            assert graph.nodes["scramble.py"]["type"] == "module"
            assert graph.nodes["print.py"]["type"] == "module"
            assert graph.nodes["Scrambler"]["type"] == "def.class"
            assert graph.nodes["Printer"]["type"] == "def.class"
            assert graph.nodes["scramble"]["type"] == "def.function"
            assert graph.nodes["print"]["type"] == "def.function"
            # check node labels
            assert graph.nodes["main.py"]["label"] == "main.py"
            assert graph.nodes["scramble.py"]["label"] == "scramble.py"
            assert graph.nodes["print.py"]["label"] == "print.py"
            assert graph.nodes["Scrambler"]["label"] == "Scrambler"
            assert graph.nodes["Printer"]["label"] == "Printer"
            assert graph.nodes["scramble"]["label"] == "scramble"
            assert graph.nodes["print"]["label"] == "print"
            # check node parents
            assert graph.nodes["main.py"]["parent"] == ""
            assert graph.nodes["scramble.py"]["parent"] == ""
            assert graph.nodes["print.py"]["parent"] == ""
            assert graph.nodes["Scrambler"]["parent"] == "scramble.py"
            assert graph.nodes["Printer"]["parent"] == "print.py"
            assert graph.nodes["scramble"]["parent"] == "scramble.py"
            assert graph.nodes["print"]["parent"] == "print.py" 
            # check edges
            assert len(graph.edges) > 0
            assert len(graph.edges) == 6
            assert graph.number_of_edges() == 6
            assert graph.has_edge("main.py", "scramble.py")
            assert graph.has_edge("main.py", "print.py")
            assert graph.has_edge("scramble.py", "Scrambler")
            assert graph.has_edge("scramble.py", "scramble")
            assert graph.has_edge("print.py", "Printer")
            assert graph.has_edge("print.py", "print")

    except Exception as e:
        # Raise exception
        raise e
