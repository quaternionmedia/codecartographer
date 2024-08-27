import { RequestHandler } from './request_handler';
import { readFile } from '../utility';

export class RepoService {
  /** Get the directories and files from a given GitHub URL. */
  public static async getGithubRepo(
    repo_url: string,
    proc_url: string
  ): Promise<any> {
    if (repo_url[repo_url.length - 1] !== '/') repo_url += '/';
    const url = `${proc_url}/parser/url?url=${encodeURIComponent(repo_url)}`;
    const data = await RequestHandler.getRequest(url);
    if (typeof data === 'string') {
      console.log('Error getGithubRepo');
      return null;
    }
    return data;
  }

  /** Parse the content of the selected file. */
  public static async parseFile(file: File, proc_url: string): Promise<any> {
    const fileRaw = await readFile(file);
    const parseBody = { name: file.name, size: file.size, raw: fileRaw };
    const urlParser = `${proc_url}/parser/file`;
    const data = await RequestHandler.postRequest(urlParser, parseBody);
    if (typeof data === 'string') {
      console.log('Error plotFile: parser');
      return null;
    }
    return data;
  }
}
