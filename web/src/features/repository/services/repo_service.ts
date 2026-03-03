import { RequestHandler } from '../../../services/request_handler';
import { Directory, RawFolder } from '../../../components/models/source';
import { logger } from '../../../core/logger';

export class RepoService {
  /** Get the directories and files from a given GitHub URL. */
  public static async getGithubRepo(
    repoUrl: string,
    repoApi: string
  ): Promise<Directory> {
    if (repoUrl[repoUrl.length - 1] !== '/') repoUrl += '/';
    const url = `${repoApi}/tree?url=${encodeURIComponent(repoUrl)}`;
    const data: Directory = await RequestHandler.getRequest(url) as Directory;
    logger.debug('RepoService.getGithubRepo: data: ', data);
    return data;
  }

  /**
   * Fetch one level of a specific path inside a GitHub repo.
   * Used to lazily expand stub folders returned by the shallow-mode tree endpoint.
   */
  public static async getSubtree(
    repoUrl: string,
    path: string,
    repoApi: string
  ): Promise<RawFolder> {
    if (repoUrl[repoUrl.length - 1] !== '/') repoUrl += '/';
    const url = `${repoApi}/subtree?url=${encodeURIComponent(repoUrl)}&path=${encodeURIComponent(path)}`;
    const data: RawFolder = await RequestHandler.getRequest(url) as RawFolder;
    logger.debug('RepoService.getSubtree:', path, data);
    return data;
  }

  /**
   * Expand all folders in a partial repo tree to the given depth (structure only, no file content).
   * Returns a full Directory with is_partial=false.
   */
  public static async expandAllTree(
    repoUrl: string,
    repoApi: string,
    maxDepth = 3
  ): Promise<Directory | null> {
    if (repoUrl[repoUrl.length - 1] !== '/') repoUrl += '/';
    const params = new URLSearchParams({ url: repoUrl, max_depth: String(maxDepth) });
    const data = await RequestHandler.getRequest(`${repoApi}/expand-all?${params}`) as Directory | null;
    logger.debug('RepoService.expandAllTree: depth=%d result:', maxDepth, data);
    return data;
  }
}
