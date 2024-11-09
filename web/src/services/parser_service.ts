import { readFile } from '../utility';
import { RequestHandler } from './request_handler';

/** NOTE: CURRENTLY UNUSED  */

export class ParserService {
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
