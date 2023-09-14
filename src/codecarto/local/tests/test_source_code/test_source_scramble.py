import random


class Scrambler:
    def scramble(self, s: str) -> str:
        chars = list(s)
        random.shuffle(chars)
        return "".join(chars)
