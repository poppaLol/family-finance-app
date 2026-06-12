from grm_rs import GraphSession


class FinanceStore:
    def __init__(self, graph: GraphSession) -> None:
        self.graph = graph
