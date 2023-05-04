import os
import tempfile

from codecarto.src.codecarto.parser import SourceParser


def test_parser():
    # setup the test environment and data
    temp_dir = tempfile.TemporaryDirectory()

    # Create sample project files
    main_file_path = os.path.join(temp_dir.name, "main.py")
    scramble_file_path = os.path.join(temp_dir.name, "scramble.py")
    print_file_path = os.path.join(temp_dir.name, "print.py")

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

    # Test the parser
    try:
        # send files in a list to parser
        source_files = [main_file_path, scramble_file_path, print_file_path]
        parser = SourceParser(source_files)

        # get back parser's graph
        graph = parser.graph

        # check if the output is correct (customize this part as needed)
        assert len(graph.nodes) > 0
    except Exception as e:
        raise e
    finally:
        # Clean up temporary files
        temp_dir.cleanup()
