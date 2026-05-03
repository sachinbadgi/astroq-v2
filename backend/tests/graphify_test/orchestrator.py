from tests.graphify_test.graph_index import GraphIndex
from astroq.lk_prediction.tracer import GraphTracer

class GraphifyTestOrchestrator:
    def __init__(self, graph_path):
        self.index = GraphIndex(graph_path)
        self.tracer = GraphTracer()

    def start_trace(self):
        return self.tracer
