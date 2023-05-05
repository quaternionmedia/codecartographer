from scramble import Scrambler
from print import Printer

input_str = "Hello, World!"
scrambler = Scrambler()
printer = Printer()
scrambled_str = scrambler.scramble(input_str)
printer.print(scrambled_str)
