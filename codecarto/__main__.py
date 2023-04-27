import sys
from src.codecarto.cli import run
from pprint import pprint

if __name__ == "__main__":
    pprint("codecarto start from top level")
    run(sys.argv[1:])
