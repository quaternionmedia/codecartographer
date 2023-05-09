from .test_source_scramble import Scrambler
from .test_source_print import Printer

input_str = "Let's do some tests!"
scrambler = Scrambler()
printer = Printer()
scrambled_str = scrambler.scramble(input_str)
printer.print(scrambled_str)
