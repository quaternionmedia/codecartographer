import m from 'mithril';

/**
 * Request data from the given API url.
 * @param url
 * @returns {Promise<Object>} - The data from the API.
 */
export async function Request(url: string): Promise<Object> {
  try {
    const response = await fetch(url);
    const responseData = await response.json();
    if (response.ok) {
      if (responseData.status !== 200) {
        // some error occurred with the backend
        console.log(
          'Request - ',
          responseData.message + ':',
          `Error with response data: ${responseData.detail}`
        );
        return responseData.message;
      } else {
        // Success - return the data
        const data = responseData.results;
        return data;
      }
    } else {
      // some error occured in the backend
      if (responseData.message.includes('GithubNoDataError')) {
        return 'Could not read Github url';
      }
    }
  } catch (error) {
    // some error occurred with the fetch
    console.log('Request - ', 'JS Error:', `Error: ${error}`);
    return 'Error fetching data';
  }
  return 'No content received';
}

/**
 * Send a POST request to the given API url.
 * @param url
 * @param formData
 * @returns
 */
export async function PostRequest(
  url: string,
  formData: FormData
): Promise<any> {
  try {
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      headers: {
        Accept: 'application/json',
      },
    });

    if (!response.ok) {
      const errorResponse = await response.text();
      throw new Error(
        `Error: ${response.status} ${response.statusText} - ${errorResponse}`
      );
    }

    const responseData = await response.json();

    if (!responseData) {
      // some error occurred with the backend
      console.log(
        'Request - ',
        ':',
        `Error with response data: ${responseData}`
      );
      return 'No content received';
    } else {
      // success
      return responseData.results;
    }
  } catch (error) {
    // some error occurred with the fetch
    console.log('Request - ', 'JS Error:', `Error: ${error}`);
    return 'Error fetching data';
  }
}
