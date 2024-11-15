import { displayError } from '../utility';

export class RequestHandler {
  /** Request data from the given API url. */
  public static async getRequest(url: string): Promise<any> {
    try {
      const response = await fetch(url);
      return this.handleResponse(response);
    } catch (error) {
      displayError(error.message);
      return null;
    }
  }

  /** Send a POST request to the given API url with customizable body and headers. */
  public static async postRequest(
    url: string,
    data: any,
    headers: Record<string, string> = {}
  ): Promise<any> {
    // Determine the default Content-Type based on the data type
    let body: any;
    let defaultHeaders: Record<string, string> = {
      Accept: 'application/json',
    };

    // Set the body and headers based on the data type
    if (data instanceof FormData) {
      body = data;
      defaultHeaders['enctype'] = 'multipart/form-data';
    } else if (typeof data === 'string') {
      body = data;
      defaultHeaders['Content-Type'] = 'text/plain';
    } else {
      body = JSON.stringify(data);
      defaultHeaders['Content-Type'] = 'application/json';
    }

    try {
      // Merge default headers with custom headers
      const mergedHeaders = { ...defaultHeaders, ...headers };
      const response = await fetch(url, {
        method: 'POST',
        body: body,
        headers: mergedHeaders,
      });

      return this.handleResponse(response);
    } catch (error) {
      displayError(error);
      return null;
    }
  }

  /** Handle the response from the API. */
  private static async handleResponse(response: Response): Promise<Object> {
    // Check if the response data is null
    const responseData = await response.json();
    if (!responseData) {
      throw new Error(
        `Request: Error with response data - No content received`
      );
    }

    // Check if the response data is an error
    if (responseData.status !== 200) {
      if (responseData.message.includes('GithubNoDataError')) {
        throw new Error('Could not read Github url');
      } else {
        // Extract the error message from the response data
        let message = responseData.message
          .split('\n\tmessage:')[2]
          .split('\n\t')[0]
          .trim();
        displayError(message);
        throw new Error(
          `Request: ${responseData.message} - ${responseData.detail}`
        );
      }
    }

    // Check if the response data is empty
    const data = responseData.results;
    if (!data) {
      throw new Error('No content received');
    }

    // TODO: Look for more specific error includes than 'Error'
    // // Check if the response data is an error
    // if (typeof data === 'string' && data.includes('Error')) {
    //   throw new Error(`Error with response data - ${data}`);
    // }

    // Return the response data
    return data;
  }
}
