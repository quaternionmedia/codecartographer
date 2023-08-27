# For more information, please refer to https://aka.ms/vscode-docker-python
FROM tiangolo/uvicorn-gunicorn:python3.11 



# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
COPY ./src/codecarto/processor/requirements_processor.txt .
RUN python -m pip install -r requirements_processor.txt

# Directory
WORKDIR /app
COPY ./src/codecarto/processor /app
ENV PYTHONPATH=/

# # Creates a non-root user with an explicit UID and adds permission to access the /codecarto folder
# # For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
# RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /codecarto
# USER appuser

# # During debugging, this entry point will be overridden. 
# For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["gunicorn", "--bind", "0.0.0.0:2000", "-k", "uvicorn.workers.UvicornWorker", "main:app"]