import { RequestHandler } from './request_handler';
import { readFile } from '../utility';

class FileData {
  name: string;
  raw: string;
}

class FolderData {
  name: string;
  files: FileData[];
}

class SourceData {
  owner: string; // quaternionmedia
  repo: string; // moe
  folders: FolderData[];
}

export class PlotService {
  /** Plot the content of the repo URL. */
  public static async plotGithubWhole(
    url: string,
    proc_url: string
  ): Promise<any> {
    const repo_url = `/plotter/repo?url=${encodeURIComponent(url)}`;
    const body = {
      options: {
        palette_id: 0,
        layout: 'Spring',
        type: 'd3',
      },
    };
    const data = await this.sendPlotRequest(proc_url, repo_url, body);
    if (typeof data === 'string') {
      console.log('Error plotGithubUrl');
      return null;
    }
    return data;
  }

  /** Plot the content of the selected URL. */
  public static async plotGithubFile(
    url: string,
    proc_url: string
  ): Promise<any> {
    const repo_url = `/plotter/url?url=${encodeURIComponent(url)}`;
    const body = {
      options: {
        palette_id: 0,
        layout: 'Spring',
        type: 'd3',
      },
    };
    const data = await this.sendPlotRequest(proc_url, repo_url, body);
    if (typeof data === 'string') {
      console.log('Error plotGithubUrl');
      return null;
    }
    return data;
  }

  /** Plot the content of the selected file. */
  public static async plotFile(file: File, proc_url: string): Promise<any> {
    // temporary solution to send raw data to the plotter
    const plotBody = {
      file: {
        name: file.name,
        size: file.size,
        raw: await readFile(file),
      },
      options: { layout: 'Spectral' },
    };
    const data = await this.sendPlotRequest(
      proc_url,
      '/plotter/file',
      plotBody
    );
    if (typeof data === 'string') {
      console.log('Error plotFile: plotter');
      return null;
    }
    return data;
  }

  /** Send SourceData to the processor to plot the data. */
  public static async plotSourceData(
    source: SourceData,
    proc_url: string
  ): Promise<any> {
    const body = new FormData();
    body.append('json_graph', JSON.stringify(source));
    body.append('options', JSON.stringify({ layout: 'Spectral' }));
    const data = await this.sendPlotRequest(proc_url, '/plotter/json', body);
    if (typeof data === 'string') {
      console.log('Error plotSourceData');
      return null;
    }
    return data;
  }

  /** Plot the content of the selected file. */
  private static async sendPlotRequest(
    proc_url: string,
    endpoint: string,
    body: any
  ): Promise<any> {
    const url = `${proc_url}${endpoint}`;
    const data = await RequestHandler.postRequest(url, body);
    if (typeof data === 'string') {
      console.log('Error sendPlotRequest');
      return null;
    }
    return data;
  }
}
