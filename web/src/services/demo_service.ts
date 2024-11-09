export async function handleDemoData(): Promise<Object[]> {
  const data_file = '/demo/demo.txt';
  const data = (await fetch(data_file)
    .then((response) => {
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.json();
    })
    .catch((error) => {
      console.error('Error fetching the data file:', error);
    })) as Object[];
  return data;
}
