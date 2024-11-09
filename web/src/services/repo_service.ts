import { readFile } from '../utility';
import { RequestHandler } from './request_handler';
import { Directory } from '../components/models/source';

export class RepoService {
  /** Get the directories and files from a given GitHub URL. */
  public static async getGithubRepo(
    repoUrl: string,
    parserUrl: string
  ): Promise<Directory> {
    if (repoUrl[repoUrl.length - 1] !== '/') repoUrl += '/';
    const url = `${parserUrl}/url?url=${encodeURIComponent(repoUrl)}`;
    const data: Directory = await RequestHandler.getRequest(url);
    console.log('RepoService.getGithubRepo: data: ', data);
    return data;
  }

  /** Parse the content of the selected file. */
  public static async parseFile(
    file: File,
    parserUrl: string
  ): Promise<string> {
    if (!(file instanceof File))
      throw new Error('Invalid file type passed to parseFile');

    const fileRaw = await readFile(file);
    const parseBody = { name: file.name, size: file.size, raw: fileRaw };
    const url = `${parserUrl}/file`;
    const data = await RequestHandler.postRequest(url, parseBody);
    return data;
  }
}
