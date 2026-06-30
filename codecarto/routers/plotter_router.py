from pathlib import Path

from fastapi import APIRouter, Body

from codecarto.models.plot_data import PlotOptions
from codecarto.services.local_repo_service import get_local_repo
from codecarto.services.unified_parser_service import UnifiedParserService
from codecarto.util.exceptions import proc_exception
from codecarto.util.utilities import Log, generate_return

PlotterRouter = APIRouter()

# directory-only -> depth=1 (folders/files, no symbol parse).
# Everything else (the old "ast"/"dependencies" distinction) -> depth=2,
# which includes symbols AND resolved file-to-file dependency edges
# together (see UnifiedParserService.build_graph's
# _add_python_dependency_edges) — matching how every other repo in the app
# is parsed; there's no separate symbols-only vs deps-only mode anymore.
_DEMO_MODE_TO_DEPTH: dict[str, int] = {"directory": 1}


@PlotterRouter.post("/demo")
async def plot_demo(options: PlotOptions = Body(..., embed=True)) -> dict:
    """
    Generate demo graph data using the codecarto project itself, through the
    same UnifiedParserService pipeline every other repo uses.
    Returns GraphData JSON format that can be rendered with any client-side renderer.
    """
    try:
        # Use the codecarto project directory as demo data
        project_root = Path(__file__).parent.parent.parent
        codecarto_dir = project_root / "codecarto"

        # Check if codecarto directory exists, otherwise use current directory
        if not codecarto_dir.exists():
            codecarto_dir = project_root

        Log.debug(f"Generating demo from directory: {codecarto_dir}")
        Log.debug(f"[PARSE MODE] Received options.parse_by = '{options.parse_by}'")

        directory = get_local_repo(str(codecarto_dir), extensions=[".py"])
        depth = _DEMO_MODE_TO_DEPTH.get(options.parse_by, 2)

        result = UnifiedParserService.parse(
            directory, depth=depth, extensions=[".py"], layout=options.layout,
        )

        return generate_return(results=result)
    except Exception as e:
        return proc_exception(
            "plot_demo",
            "Error generating demo",
            {"options": options},
            e,
        )


@PlotterRouter.post("/render/html")
async def render_graph_to_html(graph_data: dict, options: PlotOptions) -> dict:
    """
    Accept GraphData JSON and return pre-rendered HTML visualization.
    Allows frontend to send any graph data and get HTML back for Notebook renderer.

    This endpoint converts client-side GraphData format to server-rendered HTML
    using gravis visualization library.
    """
    try:
        import gravis as gv
        import networkx as nx

        # Extract graph structure from GraphData JSON
        graph_structure = graph_data.get('graph', {})
        nodes = graph_structure.get('nodes', {})
        edges = graph_structure.get('edges', [])

        # Apply optional graph-level metadata (e.g., background color)
        graph_metadata = graph_data.get('metadata', {}) if isinstance(graph_data, dict) else {}
        if isinstance(graph_metadata, dict):
            background_color = graph_metadata.get('background_color') or graph_metadata.get('backgroundColor')
            edge_color = graph_metadata.get('edge_color') or graph_metadata.get('edgeColor')
            node_label_color = graph_metadata.get('node_label_color') or graph_metadata.get('nodeLabelColor')
            edge_label_color = graph_metadata.get('edge_label_color') or graph_metadata.get('edgeLabelColor')
            arrow_color = graph_metadata.get('arrow_color') or graph_metadata.get('arrowColor')
            node_border_color = graph_metadata.get('node_border_color') or graph_metadata.get('nodeBorderColor')
            node_label_size = graph_metadata.get('node_label_size') or graph_metadata.get('nodeLabelSize')
            edge_label_size = graph_metadata.get('edge_label_size') or graph_metadata.get('edgeLabelSize')
        else:
            background_color = None
            edge_color = None
            node_label_color = None
            edge_label_color = None
            arrow_color = None
            node_border_color = None
            node_label_size = None
            edge_label_size = None

        # Build NetworkX graph from JSON
        G = nx.DiGraph()
        graph_attrs = {
            'background_color': background_color,
            'edge_color': edge_color,
            'node_label_color': node_label_color,
            'edge_label_color': edge_label_color,
            'arrow_color': arrow_color,
            'node_border_color': node_border_color,
            'node_label_size': node_label_size,
            'edge_label_size': edge_label_size,
        }
        for key, value in graph_attrs.items():
            if value is not None:
                G.graph[key] = value

        # Handle nodes (can be dict or array format)
        if isinstance(nodes, dict):
            for node_id, node_data in nodes.items():
                if not isinstance(node_data, dict):
                    continue
                node_metadata = node_data.get('metadata') or {}
                if not isinstance(node_metadata, dict):
                    node_metadata = {}
                # Extract node attributes
                label = node_data.get('label') or node_metadata.get('label') or node_id
                color = node_data.get('color') or node_metadata.get('color') or '#00ff41'
                size = node_data.get('size') or node_metadata.get('size') or 10
                label_color = node_data.get('label_color') or node_metadata.get('label_color')
                label_size = node_data.get('label_size') or node_metadata.get('label_size')
                border_color = node_data.get('border_color') or node_metadata.get('border_color')
                border_size = node_data.get('border_size') or node_metadata.get('border_size')
                node_attrs = {
                    'label': label,
                    'color': color,
                    'size': size,
                }
                if label_color:
                    node_attrs['label_color'] = label_color
                if label_size is not None:
                    node_attrs['label_size'] = label_size
                if border_color:
                    node_attrs['border_color'] = border_color
                if border_size is not None:
                    node_attrs['border_size'] = border_size
                G.add_node(node_id, **node_attrs)
        elif isinstance(nodes, list):
            for node_data in nodes:
                if not isinstance(node_data, dict):
                    continue
                node_metadata = node_data.get('metadata') or {}
                if not isinstance(node_metadata, dict):
                    node_metadata = {}
                node_id = node_data.get('id', str(len(G.nodes)))
                label = node_data.get('label') or node_metadata.get('label') or node_id
                color = node_data.get('color') or node_metadata.get('color') or '#00ff41'
                size = node_data.get('size') or node_metadata.get('size') or 10
                label_color = node_data.get('label_color') or node_metadata.get('label_color')
                label_size = node_data.get('label_size') or node_metadata.get('label_size')
                border_color = node_data.get('border_color') or node_metadata.get('border_color')
                border_size = node_data.get('border_size') or node_metadata.get('border_size')
                node_attrs = {
                    'label': label,
                    'color': color,
                    'size': size,
                }
                if label_color:
                    node_attrs['label_color'] = label_color
                if label_size is not None:
                    node_attrs['label_size'] = label_size
                if border_color:
                    node_attrs['border_color'] = border_color
                if border_size is not None:
                    node_attrs['border_size'] = border_size
                G.add_node(node_id, **node_attrs)

        # Add edges
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            source = edge.get('source')
            target = edge.get('target')
            # Handle case where source/target might be node objects
            if isinstance(source, dict):
                source = source.get('id')
            if isinstance(target, dict):
                target = target.get('id')
            if source and target:
                edge_metadata = edge.get('metadata') or {}
                if not isinstance(edge_metadata, dict):
                    edge_metadata = {}
                edge_label = edge.get('label') or edge_metadata.get('label') or ''
                edge_color_value = edge.get('color') or edge_metadata.get('color')
                edge_label_color = edge.get('label_color') or edge_metadata.get('label_color')
                edge_label_size = edge.get('label_size') or edge_metadata.get('label_size')
                edge_attrs = {'label': edge_label}
                if edge_color_value:
                    edge_attrs['color'] = edge_color_value
                if edge_label_color:
                    edge_attrs['label_color'] = edge_label_color
                if edge_label_size is not None:
                    edge_attrs['label_size'] = edge_label_size
                G.add_edge(source, target, **edge_attrs)

        Log.debug(f"Building HTML from graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")

        # Generate HTML using gravis
        # Note: gravis reads 'color' directly from node attributes, no data_source param needed
        fig = gv.d3(
            G,
            node_label_data_source='label',
            node_size_data_source='size',
            use_node_size_normalization=True,
            node_size_normalization_max=30,
            edge_label_data_source='label',
            show_edge_label=True,
            graph_height=600,
        )
        html = fig.to_html_standalone()

        return generate_return(results={"text/html": html})
    except Exception as e:
        return proc_exception(
            "render_graph_to_html",
            "Error rendering graph to HTML",
            {"graph_data_keys": list(graph_data.keys()) if graph_data else []},
            e,
        )
