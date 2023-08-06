import os
import tempfile
from typing import Union
from fastapi import APIRouter, Response
from fastapi.responses import FileResponse
from codecarto import GraphData, Plotter, ErrorHandler

router: APIRouter = APIRouter() 
 
@router.post("/plotter/plot", request_body_max=1000000, responses={200: {"content": {"image/png": {}}}})
async def plot(
    graph_data: GraphData, layout: str = "", do_grid: bool = False, do_json: bool = False
) -> Response:
    """Plots a graph representing source code.

    Parameters:
    -----
        graph_data (GraphData): 
            The graph to plot.
        layout (str): 
            The layout to use for the plot.
        do_grid (bool): 
            Whether or not plot all layouts in a grid.
        do_json (bool): 
            Whether or not to return the json data.

    Returns:
    --------
        Response:
            The response containing the plotted image file.
    """
    if graph_data is None:
        # internal server error log
        ErrorHandler.log(caller="API/plotter/plot", break_line = 34, msg="No graph data provided.")
        raise ValueError("No graph data provided.")
    else: 
        try: 
            # Prevent abusive requests 
            # TODO: Here are a few simple measures you could consider:
            # Rate limiting:    <--- this one, slowapi lib can be used for this
            #   Limit the number of API requests that a user can make in a certain time period.
            # Size limits:      <--- this one, request_body_max=1000000 can be added to the post decorator
            #   Limit the size of the graph data that a user can submit.
            # Timeouts:         <--- this one, uvicorn main:app --timeout 30 # 30 seconds
            #   Set a maximum time limit for creating a plot. If the plot takes longer than 
            #   this limit, abort the operation and return an error.
            # Authentication and authorization: 
            #   Require users to authenticate (log in) before they can use your API, and limit 
            #   what each user is authorized to do based on their role or permissions.


            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
                tmpname = tmpfile.name

            # Plot the graph
            Plotter.plot_graph(graph=graph_data, file_name=tmpname, layout=layout, do_grid=do_grid, do_json=do_json, api=True)

            # Create a response with the file
            response = FileResponse(tmpname, media_type="image/png", filename="plot.png")
            
            # Delete the temporary file after sending it
            response.on_finish.append(lambda: os.unlink(tmpname))
             
            # Return the response image/file
            return response
        except Exception as e:
            # internal server error log
            ErrorHandler.log(exception=e, caller="API/plotter/plot", msg="Failed to plot graph.")
            raise e
