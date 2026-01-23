from pydantic import BaseModel
from typing import Optional


class GravisOptions(BaseModel):
    # Common settings for all types
    palette_id: str = "0"
    layout: str = "Spring"
    zoom_factor: float = 1.5

    # Node settings
    node_size_factor: float = 1.0
    node_size_normalization_max: float = 30.0
    use_node_size_normalization: bool = True
    node_hover_neighborhood: bool = True

    show_node_label: bool = True
    node_label_size_factor: float = 0.5
    node_label_data_source: str = "label"

    # Edge settings
    edge_size_factor: float = 1.0
    links_force_strength: float = 0.5
    links_force_distance: float = 55.0
    use_edge_size_normalization: bool = True
    use_centering_force: bool = False

    show_edge_label: bool = True
    edge_label_size_factor: float = 0.5
    edge_label_data_source: str = "label"

    # Additional properties can be shared here if needed


class GravisD3Options(GravisOptions):
    type: str = "d3"
    graph_height: int = 450
    details_height: int = 100
    show_details: bool = False
    large_graph_threshold: int = 500

    # D3-specific layout settings
    layout_algorithm_active: bool = True
    use_many_body_force: bool = True
    many_body_force_strength: float = -70.0
    many_body_force_theta: float = 0.9


class GravisThreeOptions(GravisOptions):
    type: str = "three"
    graph_height: int = 450
    details_height: int = 100
    show_details: bool = False
    large_graph_threshold: int = 200

    # Three.js specific settings
    use_z_positioning_force: bool = True
    z_positioning_force_strength: float = 0.2
    layout_algorithm_active: bool = True
    many_body_force_min_distance: Optional[float] = 10.0
    many_body_force_max_distance: Optional[float] = 1000.0


class GravisVisOptions(GravisOptions):
    type: str = "vis"
    graph_height: int = 450
    details_height: int = 100
    show_details: bool = False
    layout_algorithm: str = "barnesHut"
    gravitational_constant: float = -2000.0
    central_gravity: float = 0.1
    spring_length: float = 70.0
    spring_constant: float = 0.1
    avoid_overlap: float = 0.0
