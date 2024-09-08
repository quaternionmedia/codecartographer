import { RequestHandler } from "./request_handler";
import { readFile } from "../utility";
import { Repo, RepoInfo } from "../components/models/source";

export class RepoService {
  /** Get the directories and files from a given GitHub URL. */
  public static async getGithubRepo(
    repoUrl: string,
    procUrl: string
  ): Promise<Repo> {
    if (repoUrl[repoUrl.length - 1] !== "/") repoUrl += "/";
    const url = `${procUrl}/parser/url?url=${encodeURIComponent(repoUrl)}`;
    const data: Repo = await RequestHandler.getRequest(url);

    const repoInfo = new RepoInfo(
      data.info.owner,
      data.info.repo,
      data.info.url
    );
    return new Repo(repoInfo, data.size, data.raw);
  }

  /** Parse the content of the selected file. */
  public static async parseFile(file: File, proc_url: string): Promise<string> {
    if (!(file instanceof File)) {
      throw new Error("Invalid file type passed to parseFile");
    }

    const fileRaw = await readFile(file);
    const parseBody = { name: file.name, size: file.size, raw: fileRaw };
    const urlParser = `${proc_url}/parser/file`;
    const data = await RequestHandler.postRequest(urlParser, parseBody);
    return data;
  }
}
