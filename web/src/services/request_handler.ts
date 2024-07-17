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
        // Success: Parse the data and display it
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
