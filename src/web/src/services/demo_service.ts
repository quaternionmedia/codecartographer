export const handleDemoData = (handlePlotData: (data: any) => void) => {
  const data_file = '/demo/demo.txt';
  fetch(data_file)
    .then((response) => {
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.json();
    })
    .then((jsonData) => {
      handlePlotData(jsonData);
    })
    .catch((error) => {
      console.error('Error fetching the data file:', error);
    });
};
