async function testDatabaseWrite() {
  try {
    const test_graph_name = 'web_test_graph_name'
    const test_json_graph = {
      name: test_graph_name,
      nodes: [
        { id: '1', label: 'Node 1' },
        { id: '2', label: 'Node 2' },
      ],
      links: [{ source: '1', target: '2' }],
    }
    const test_json_graph2 = {
      nodes: [
        { id: '1', label: 'Node 1' },
        { id: '2', label: 'Node 2' },
      ],
      links: [{ source: '1', target: '2' }],
    }

    // Attempt to delete the graph if it exists.
    const responseDel = await fetch(
      `/db/graph/${encodeURIComponent(test_graph_name)}`,
      {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    )

    // Check if the deletion was successful or if the graph was not found (which is fine for insertion).
    if (responseDel.ok || responseDel.status === 404) {
      console.log('Ready to insert graph.')

      // Insert the new graph
      const response = await fetch(
        `/db/graph/insert/${encodeURIComponent(test_graph_name)}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ graph_data: test_json_graph }),
        }
      )

      // Check the response status
      if (response.ok) {
        const responseData = await response.json()
        console.log(
          `Graph inserted successfully: ${JSON.stringify(responseData)}`
        )
      } else {
        // Read the response body correctly based on the content type
        if (
          response.headers.get('content-type')?.includes('application/json')
        ) {
          const errorDetails = await response.json()
          console.error('Error details:', errorDetails)
        } else {
          const responseText = await response.text()
          console.error('Received non-JSON response:', responseText)
        }
        console.error(
          `Error with response status during insertion: ${response.status}`
        )
      }
    } else {
      console.error(
        `Error with response status during deletion: ${responseDel.status}`
      )
      return { status: 'error', message: 'Error during deletion' }
    }
  } catch (error) {
    console.error('Error - testDatabaseWrite():', error)
    return { status: 'error', message: 'Network error' }
  }
}
