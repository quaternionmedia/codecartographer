# API folder holds logic for the API endpoints and routers.
# These are called through browsers or other applications.

# These will do the MAIN functionality of the application alone.
# Things like config set up and output directories are not necessary
# since the server will have fixed output directories and configurations.

# The main functions the API will have access to are:
#  - Converting any input data to PlotGraph (PolyGraph)
#  - Parsing source code to a PlotGraph object
#  - Passing plot layouts and themes
#       TODO: how will we save these on the server?
#       Will need to have access to them when plotting
#       could we somehow have layout and theme objects passed in to the plotter?
#  - Plotting a PlotGraph object to an image
#  - ? Analyzing the graph
#       TODO: this part actually may be handled in TechOps)
# I can't think of anything else that the API will need to do.


################## Performance Metrics ##########################
#   Performance Metrics:
#       This includes timing how long it takes to process each request, how long it takes
#       to parse each file, etc. This can help you find any performance bottlenecks in your code.
#   Usage Metrics:
#       This includes how often each endpoint is hit, how many files are uploaded, how large the
#       files are, etc. This can help you understand how your API is being used and plan for scaling.
#   Error Metrics:
#       Track the number and type of errors that occur. This can help you identify the most common
#       problems and prioritize fixes.


################## Abusive Request Protection ###################
#   Rate limiting:
#       This is to prevent a single user from overwhelming your server by sending
#       too many requests in a short period of time. You can use the slowapi library
#       to apply rate limiting in FastAPI.
#   File Type Checks:
#       You may want to validate the file type of uploaded files. This can prevent
#       users from uploading potentially malicious files.
#   Error Handling:
#       Providing clear and user-friendly error messages can help users understand what
#       went wrong if their request fails. However, be careful not to provide too much
#       detail in error messages, as this could provide useful information to an attacker.
#   Logging and Monitoring:
#       Keeping logs of API usage can help you understand how your API is used and identify
#       potential security issues. Monitoring API usage can help you identify unusual patterns
#       that may indicate a security issue.
#   Authentication and Authorization:
#       Depending on your use case, you might want to require users to authenticate
#       (log in) before they can use your API, and limit what each user is authorized
#       to do based on their role or permissions.
#   Input Sanitization:
#       This involves cleaning the input to prevent injection attacks. This is especially
#       important if you're passing the user's input to a command line operation, or using
#       it to generate SQL queries, etc.
#   Timeouts:
#       If the parsing of the file takes too long, you may want to abort the operation
#       and return an error. This can prevent a user from unintentionally overwhelming
#       your server with a very complex file. You can set a timeout for requests at the
#       server level. For example, if you're using uvicorn as your ASGI server, you can
#       set the timeout like this:
#           uvicorn main:app --timeout 30  # 30 seconds
#       It means the server will automatically stop processing any request that takes
#       longer than 30 seconds.
#   Secure Transmission:
#       If your API is accessible over the internet, you should enforce HTTPS to ensure that
#       data is transmitted securely. You could use a HTTPS reverse proxy, such as Nginx or
#       Apache, to handle the HTTPS part. Basically, you configure your server to handle HTTPS
#       and then forward the requests to your FastAPI application. Another alternative would
#       be using a cloud platform like AWS or GCP, they provide options to set up HTTPS.
