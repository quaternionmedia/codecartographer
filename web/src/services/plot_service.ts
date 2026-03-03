import { RequestHandler } from './request_handler';
import { RawFile, Directory } from '../components/models/source';
import { logger } from '../core/logger';

type PlotRequestBody = Record<string, unknown> | FormData;

export class PlotService {
  /** Plot the content of the repo URL. */
  public static async plotRepoWhole(
    directory: Directory,
    plotterUrl: string,
    layout: string = 'Spring',
    parseMode: string = 'directory'
  ): Promise<unknown> {
    const body = {
      directory: {
        info: directory.info,
        size: directory.size,
        root: directory.root,
      },
      options: {
        palette_id: '0',
        layout: layout,
        type: 'd3',
        parse_by: parseMode,
      },
    };
    const data = await this.sendPlotRequest(plotterUrl, `/whole_repo`, body);
    if (typeof data === 'string') {
      logger.error('Error plotGithubUrl');
      return null;
    }
    return data;
  }

  /** Plot the content of the repo URL dependencies. */
  public static async plotRepoWholeDeps(
    directory: Directory,
    plotterUrl: string,
    layout: string = 'Kamada_Kawai',
    parseMode: string = 'dependencies'
  ): Promise<unknown> {
    const body = {
      directory: {
        info: directory.info,
        size: directory.size,
        root: directory.root,
      },
      options: {
        palette_id: '0',
        layout: layout,
        type: 'd3',
        parse_by: parseMode,
      },
    };
    const data = await this.sendPlotRequest(
      plotterUrl,
      `/whole_repo`,
      body
    );
    if (typeof data === 'string') {
      logger.error('Error plotGithubUrl');
      return null;
    }
    return data;
  }

  /** Plot the content of the selected URL. */
  public static async plotUrlFile(
    url: string,
    plotterUrl: string,
    layout: string = 'Spring'
  ): Promise<unknown> {
    const repo_url = `/url?url=${encodeURIComponent(url)}`;
    const body = {
      options: {
        palette_id: '0',
        layout: layout,
        type: 'd3',
      },
    };
    const data = await this.sendPlotRequest(plotterUrl, repo_url, body);
    if (typeof data === 'string') {
      logger.error('Error plotGithubUrl');
      return null;
    }
    return data;
  }

  /** Plot the content of the selected file. */
  public static async plotFile(
    file: RawFile,
    plotterUrl: string,
    layout: string = 'Spectral',
    parseMode: string = 'ast'
  ): Promise<unknown> {
    // temporary solution to send raw data to the plotter
    logger.debug('plotFile: ', file);
    const plotBody = {
      file: {
        url: file.url,
        name: file.name,
        size: file.size,
        raw: file.raw,
      },
      options: {
        palette_id: '0',
        layout: layout,
        type: 'd3',
        parse_by: parseMode,
      },
    };
    const data = await this.sendPlotRequest(plotterUrl, '/file', plotBody);
    if (typeof data === 'string') {
      logger.error('Error plotFile: plotter');
      return null;
    }
    return data;
  }

  /** Send Source to the processor to plot the data. */
  public static async plotSourceData(
    source: Directory,
    plotterUrl: string,
    layout: string = 'Spectral'
  ): Promise<unknown> {
    const body = new FormData();
    body.append('json_graph', JSON.stringify(source));
    body.append('options', JSON.stringify({ layout: layout }));
    const data = await this.sendPlotRequest(plotterUrl, '/json', body);
    if (typeof data === 'string') {
      logger.error('Error plotSourceData');
      return null;
    }
    return data;
  }

  /** Load demo data from backend. */
  public static async loadDemo(
    plotterUrl: string,
    layout: string = 'Spring',
    parseMode: string = 'directory'
  ): Promise<unknown> {
    const body = {
      options: {
        palette_id: '0',
        layout: layout,
        type: 'd3',
        parse_by: parseMode,
      },
    };
    console.log(`[PARSE MODE] PlotService.loadDemo - sending request with parse_by=${parseMode}`);
    const data = await this.sendPlotRequest(plotterUrl, '/demo', body);
    if (typeof data === 'string') {
      logger.error('Error loading demo');
      return null;
    }
    return data;
  }

  /**
   * Convert GraphData JSON to pre-rendered HTML for Notebook renderer.
   * Sends graph data to backend which renders it using gravis and returns HTML.
   */
  public static async renderToHtml(
    plotterUrl: string,
    graphData: unknown,
    layout: string = 'Spring'
  ): Promise<{ 'text/html': string } | null> {
    const body = {
      graph_data: graphData,
      options: {
        layout: layout,
      },
    };
    const data = await this.sendPlotRequest(plotterUrl, '/render/html', body);
    if (typeof data === 'string' || !data) {
      logger.error('Error rendering to HTML');
      return null;
    }
    // RequestHandler already extracts responseData.results, so data IS the results object
    // Expected format: { "text/html": "<html>..." }
    const result = data as { 'text/html'?: string };
    if (result['text/html']) {
      return { 'text/html': result['text/html'] };
    }
    logger.error('Invalid response format from renderToHtml:', data);
    return null;
  }

  /** Parse a C/C++ file via the c-parser backend endpoint. */
  public static async plotCFile(
    cParserUrl: string,
    path: string
  ): Promise<unknown> {
    const url = `${cParserUrl}/file`;
    const body = { path };
    const data = await RequestHandler.postRequest(url, body);
    if (typeof data === 'string') {
      logger.error('Error plotCFile');
      return null;
    }
    return data;
  }

  /** Download a GitHub repo and parse it as a C/C++ semantic graph. */
  public static async plotCGithub(
    cParserUrl: string,
    repoUrl: string,
    maxFiles: number = 200
  ): Promise<unknown> {
    const url = `${cParserUrl}/github`;
    const body = { url: repoUrl, max_files: maxFiles };
    const data = await RequestHandler.postRequest(url, body);
    if (typeof data === 'string') {
      logger.error('Error plotCGithub');
      return null;
    }
    return data;
  }

  /** Parse a C/C++ directory via the c-parser backend endpoint. */
  public static async plotCDirectory(
    cParserUrl: string,
    path: string
  ): Promise<unknown> {
    const url = `${cParserUrl}/directory`;
    const body = { path };
    const data = await RequestHandler.postRequest(url, body);
    if (typeof data === 'string') {
      logger.error('Error plotCDirectory');
      return null;
    }
    return data;
  }

  /** Fetch the registered language extensions from the backend. */
  public static async fetchLanguages(
    parseUrl: string
  ): Promise<Record<string, string[]> | null> {
    const data = await RequestHandler.getRequest(`${parseUrl}/languages`) as Record<string, unknown> | null;
    return (data?.['languages'] as Record<string, string[]>) ?? null;
  }

  /** Parse a directory using the unified schema (depth-based hierarchy). */
  public static async plotUnified(
    parseUrl: string,
    directory: Directory,
    depth: number = 2,
    extensions: string[] | null = null,
    layout: string = 'Spring',
    mode?: string
  ): Promise<unknown> {
    const url = `${parseUrl}/unified`;
    const body: Record<string, unknown> = {
      directory: {
        info: directory.info,
        size: directory.size,
        root: directory.root,
        is_partial: directory.is_partial,
      },
      depth,
      layout,
    };
    if (extensions) {
      body['extensions'] = extensions;
    }
    if (mode) {
      body['mode'] = mode;
    }
    const data = await RequestHandler.postRequest(url, body);
    if (typeof data === 'string') {
      logger.error('Error plotUnified');
      return null;
    }
    return data;
  }

  /** Expand a single file node to reveal its symbols. */
  public static async expandNode(
    parseUrl: string,
    directory: Directory,
    nodeId: string,
    depth: number = 2
  ): Promise<unknown> {
    const url = `${parseUrl}/expand`;
    const body = {
      directory: {
        info: directory.info,
        size: directory.size,
        root: directory.root,
        is_partial: directory.is_partial,
      },
      node_id: nodeId,
      depth,
    };
    const data = await RequestHandler.postRequest(url, body);
    if (typeof data === 'string') {
      logger.error('Error expandNode');
      return null;
    }
    return data;
  }

  /** Plot the content of the selected file. */
  private static async sendPlotRequest(
    plotterUrl: string,
    endpoint: string,
    body: PlotRequestBody
  ): Promise<unknown> {
    const url = `${plotterUrl}${endpoint}`;
    logger.debug('PlotService.sendPlotRequest - sending to:', url, 'body:', body);
    const data = await RequestHandler.postRequest(url, body);
    logger.debug('PlotService.sendPlotRequest - response:', data);
    if (typeof data === 'string') {
      logger.error('Error sendPlotRequest - got string response');
      return null;
    }
    return data;
  }
}
