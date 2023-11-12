import bashlex
import networkx as nx


class ShellDiGraphConstructor:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.node_counter = 0

    def create_new_node(self, node_type, node_label, parent_id=None):
        self.node_counter += 1
        node_id = self.node_counter
        self.graph.add_node(node_id, type=node_type, label=node_label)
        if parent_id is not None:
            self.graph.add_edge(parent_id, node_id)
        return node_id

    def visit(self, parts, parent_id=None):
        for part in parts:
            if isinstance(part, bashlex.ast.node):
                if part.kind == "command":
                    self.handle_command(part, parent_id)
                # Handle other types similarly...
                else:
                    self.visit(part.parts, parent_id)

    def handle_command(self, command_node, parent_id):
        # Commands can have multiple parts, e.g., 'echo $HOME'
        command_id = self.create_new_node(
            "command", command_node.parts[0].word, parent_id
        )
        for part in command_node.parts[1:]:
            # Add each argument as a child node
            self.create_new_node("word", part.word, command_id)


def parse_shell_script(script):
    nodes = bashlex.parse(script)
    digraph_constructor = ShellDiGraphConstructor()
    digraph_constructor.visit(nodes)
    return digraph_constructor.graph
