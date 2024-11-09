import { RequestHandler } from './request_handler';
import { Directory } from '../components/models/source';

export class RepoService {
  /** Get the directories and files from a given GitHub URL. */
  public static async getGithubRepo(
    repoUrl: string,
    repoApi: string
  ): Promise<Directory> {
    if (repoUrl[repoUrl.length - 1] !== '/') repoUrl += '/';
    const url = `${repoApi}/tree?url=${encodeURIComponent(repoUrl)}`;
    const data: Directory = await RequestHandler.getRequest(url);
    console.log('RepoService.getGithubRepo: data: ', data);
    return data;
  }
}
