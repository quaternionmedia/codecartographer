/**
 * Request data from the given API url.
 * @param url
 * @returns {Promise<Object>} - The data from the API.
 * @throws {Error} - The error message from the API.
 */
export async function GetRequest(url: string): Promise<Object> {
  const response = await fetch(url);
  return handleResponse(response);
}

/**
 * Send a POST request to the given API url.
 * @param url
 * @param formData
 * @returns {Promise<Object>} - The data from the API.
 * @throws {Error} - The error message from the API.
 */
export async function PostRequest(
  url: string,
  formData: FormData
): Promise<any> {
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
    headers: {
      Accept: 'application/json',
      enctype: 'multipart/form-data',
    },
  });
  return handleResponse(response);
}

/**
 * Send a POST request with JSON data to the given API url.
 * @param url
 * @param jsonData
 * @returns {Promise<Object>} - The data from the API.
 * @throws {Error} - The error message from the API.
 */
export async function PostJsonRequest(
  url: string,
  jsonData: any
): Promise<any> {
  const response = await fetch(url, {
    method: 'POST',
    body: JSON.stringify(jsonData),
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
  });
  return handleResponse(response);
}

/**
 * Send a POST request with string data to the given API url.
 * @param url
 * @param data
 * @returns {Promise<Object>} - The data from the API.
 * @throws {Error} - The error message from the API.
 */
export async function PostStringRequest(
  url: string,
  data: string
): Promise<any> {
  const response = await fetch(url, {
    method: 'POST',
    body: data,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'text/plain',
    },
  });
  return handleResponse(response);
}

/**
 * Handle the response from the fetch request.
 * @param response
 * @param isRepoRead
 * @returns {Promise<Object>} - The data from the API.
 * @throws {Error} - The error message from the API.
 */
async function handleResponse(response: Response): Promise<any> {
  // Check if the response is ok
  if (!response.ok) {
    const errorResponse = await response.text();
    throw new Error(
      `Error: ${response.status} ${response.statusText} - ${errorResponse}`
    );
  }

  // Check if the response data is null
  const responseData = await response.json();
  if (!responseData) {
    throw new Error(
      `Error: Request - Error with response data - No content received`
    );
  }

  // Check if the response data is an error
  if (responseData.status !== 200) {
    if (responseData.message.includes('GithubNoDataError')) {
      throw new Error('Could not read Github url');
    } else {
      throw new Error(
        `Error: Request - ${responseData.message} - ${responseData.detail}`
      );
    }
  }

  // Success
  return responseData.results;
}
