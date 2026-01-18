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
        layout: layout,
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
    const data = await this.sendPlotRequest(plotterUrl, '/demo', body);
    if (typeof data === 'string') {
      logger.error('Error loading demo');
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
