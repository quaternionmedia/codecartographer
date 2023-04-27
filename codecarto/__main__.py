import sys
from src.cli import parse_args
from pprint import pprint

if __name__ == "__main__":
    pprint("codecarto start")
    parse_args(sys.argv[1:])
