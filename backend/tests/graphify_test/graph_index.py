import json
import os

class GraphIndex:
    def __init__(self, graph_path):
        self.graph_path = graph_path
        self.nodes_by_id = {}
        self.nodes_by_label = {}
        self._load_graph()

    def _load_graph(self):
        if not os.path.exists(self.graph_path):
            return

        with open(self.graph_path, 'r') as f:
            data = json.load(f)
            nodes = data.get('nodes', [])
            for node in nodes:
                node_id = node.get('id')
                if node_id:
                    self.nodes_by_id[node_id] = node
                
                label = node.get('norm_label')
                if label:
                    if label not in self.nodes_by_label:
                        self.nodes_by_label[label] = []
                    self.nodes_by_label[label].append(node)

    def get_node_by_id(self, node_id):
        return self.nodes_by_id.get(node_id)

    def get_nodes_by_label(self, label):
        return self.nodes_by_label.get(label, [])
