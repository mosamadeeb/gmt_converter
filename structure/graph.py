from typing import List


class Graph:
    def __init__(self):
        self.keyframes = []

    keyframes = List[int]
    delimiter = int  # either FF or 0


def zero_graph():
    zero = Graph()
    zero.keyframes = [0]
    zero.delimiter = -1
    return zero
