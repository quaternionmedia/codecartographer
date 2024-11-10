/**
 * Base settings for Gravis visualizations.
 */
export class GravisOptions {
  paletteId: string;
  layout: string;
  zoomFactor: number;

  nodeSizeFactor: number;
  nodeSizeNormalizationMax: number;
  useNodeSizeNormalization: boolean;
  nodeHoverNeighborhood: boolean;

  showNodeLabel: boolean;
  nodeLabelSizeFactor: number;
  nodeLabelDataSource: string;

  edgeSizeFactor: number;
  linksForceStrength: number;
  linksForceDistance: number;
  useEdgeSizeNormalization: boolean;
  useCenteringForce: boolean;

  showEdgeLabel: boolean;
  edgeLabelSizeFactor: number;
  edgeLabelDataSource: string;

  constructor() {
    this.paletteId = '0';
    this.layout = 'Spring';
    this.zoomFactor = 1.5;

    this.nodeSizeFactor = 1.0;
    this.nodeSizeNormalizationMax = 30.0;
    this.useNodeSizeNormalization = true;
    this.nodeHoverNeighborhood = true;

    this.showNodeLabel = true;
    this.nodeLabelSizeFactor = 0.5;
    this.nodeLabelDataSource = 'label';

    this.edgeSizeFactor = 1.0;
    this.linksForceStrength = 0.5;
    this.linksForceDistance = 55;
    this.useEdgeSizeNormalization = true;
    this.useCenteringForce = false;

    this.showEdgeLabel = true;
    this.edgeLabelSizeFactor = 0.5;
    this.edgeLabelDataSource = 'label';
  }
}

/**
 * Settings specific to D3-based Gravis visualization.
 */
export class GravisD3Options extends GravisOptions {
  type: string;
  graphHeight: number;
  detailsHeight: number;
  showDetails: boolean;
  largeGraphThreshold: number;

  layoutAlgorithmActive: boolean;
  useManyBodyForce: boolean;
  manyBodyForceStrength: number;
  manyBodyForceTheta: number;

  constructor() {
    super();
    this.type = 'd3';
    this.graphHeight = 450;
    this.detailsHeight = 100;
    this.showDetails = false;
    this.largeGraphThreshold = 500;

    this.layoutAlgorithmActive = true;
    this.useManyBodyForce = true;
    this.manyBodyForceStrength = -70.0;
    this.manyBodyForceTheta = 0.9;
  }
}

/**
 * Settings specific to Three.js-based Gravis visualization.
 */
export class GravisThreeOptions extends GravisOptions {
  type: string;
  graphHeight: number;
  detailsHeight: number;
  showDetails: boolean;
  largeGraphThreshold: number;

  useZPositioningForce: boolean;
  zPositioningForceStrength: number;
  layoutAlgorithmActive: boolean;
  manyBodyForceMinDistance: number;
  manyBodyForceMaxDistance: number;

  constructor() {
    super();
    this.type = 'three';
    this.graphHeight = 450;
    this.detailsHeight = 100;
    this.showDetails = false;
    this.largeGraphThreshold = 200;

    this.useZPositioningForce = true;
    this.zPositioningForceStrength = 0.2;
    this.layoutAlgorithmActive = true;
    this.manyBodyForceMinDistance = 10.0;
    this.manyBodyForceMaxDistance = 1000.0;
  }
}

/**
 * Settings specific to Vis.js-based Gravis visualization.
 */
export class GravisVisOptions extends GravisOptions {
  type: string;
  graphHeight: number;
  detailsHeight: number;
  showDetails: boolean;
  layoutAlgorithm: string;
  gravitationalConstant: number;
  centralGravity: number;
  springLength: number;
  springConstant: number;
  avoidOverlap: number;

  constructor() {
    super();
    this.type = 'vis';
    this.graphHeight = 450;
    this.detailsHeight = 100;
    this.showDetails = false;
    this.layoutAlgorithm = 'barnesHut';
    this.gravitationalConstant = -2000.0;
    this.centralGravity = 0.1;
    this.springLength = 70.0;
    this.springConstant = 0.1;
    this.avoidOverlap = 0.0;
  }
}
