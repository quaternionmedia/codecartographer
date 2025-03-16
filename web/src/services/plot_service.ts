import { RequestHandler } from './request_handler';
import { RawFile, Directory } from '../components/models/source';

export class PlotService {
  /** Plot the content of the repo URL. */
  public static async plotRepoWhole(
    directory: Directory,
    plotterUrl: string
  ): Promise<any> {
    //const mode = document.querySelector('.switch_text')!.textContent;
    const body = {
      directory: directory,
      options: {
        palette_id: '0',
        layout: 'Spring',
        type: 'd3',
        //parse_by: mode,
      },
    };
    const data = await this.sendPlotRequest(plotterUrl, `/whole_repo`, body);
    if (typeof data === 'string') {
      console.log('Error plotGithubUrl');
      return null;
    }
    return data;
  }

  /** Plot the content of the repo URL. */
  public static async plotRepoWholeDeps(
    directory: Directory,
    plotterUrl: string
  ): Promise<any> {
    //const mode = document.querySelector('.switch_text')!.textContent;
    const body = {
      directory: directory,
      options: {
        palette_id: '0',
        layout: 'Kamada_Kawai',
        type: 'd3',
        //parse_by: mode,
      },
    };
    const data = await this.sendPlotRequest(
      plotterUrl,
      `/whole_repo_deps`,
      body
    );
    if (typeof data === 'string') {
      console.log('Error plotGithubUrl');
      return null;
    }
    return data;
  }

  /** Plot the content of the selected URL. */
  public static async plotUrlFile(
    url: string,
    plotterUrl: string
  ): Promise<any> {
    const repo_url = `/url?url=${encodeURIComponent(url)}`;
    const body = {
      options: {
        palette_id: '0',
        layout: 'Spring',
        type: 'd3',
      },
    };
    const data = await this.sendPlotRequest(plotterUrl, repo_url, body);
    if (typeof data === 'string') {
      console.log('Error plotGithubUrl');
      return null;
    }
    return data;
  }

  /** Plot the content of the selected file. */
  public static async plotFile(
    file: RawFile,
    plotterUrl: string
  ): Promise<any> {
    // temporary solution to send raw data to the plotter
    console.log('plotFile: ', file);
    const plotBody = {
      file: file,
      options: { layout: 'Spectral' },
    };
    const data = await this.sendPlotRequest(plotterUrl, '/file', plotBody);
    if (typeof data === 'string') {
      console.log('Error plotFile: plotter');
      return null;
    }
    return data;
  }

  /** Send Source to the processor to plot the data. */
  public static async plotSourceData(
    source: Directory,
    plotterUrl: string
  ): Promise<any> {
    const body = new FormData();
    body.append('json_graph', JSON.stringify(source));
    body.append('options', JSON.stringify({ layout: 'Spectral' }));
    const data = await this.sendPlotRequest(plotterUrl, '/json', body);
    if (typeof data === 'string') {
      console.log('Error plotSourceData');
      return null;
    }
    return data;
  }

  /** Plot the content of the selected file. */
  private static async sendPlotRequest(
    plotterUrl: string,
    endpoint: string,
    body: any
  ): Promise<any> {
    const url = `${plotterUrl}${endpoint}`;
    const data = await RequestHandler.postRequest(url, body);
    if (typeof data === 'string') {
      console.log('Error sendPlotRequest');
      return null;
    }
    return data;
  }
}
