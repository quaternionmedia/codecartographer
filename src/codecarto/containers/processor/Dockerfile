FROM tiangolo/uvicorn-gunicorn:python3.11 

EXPOSE 2020

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
COPY ./src/codecarto/containers/processor/requirements.txt .
RUN python -m pip install -r requirements.txt

# Directory
WORKDIR /app
COPY ./src/codecarto/containers/processor/api /app/api
COPY ./src/codecarto/containers/processor/src /app/src
ENV PYTHONPATH=/app

# # Creates a non-root user with an explicit UID and adds permission to access the /app folder
# # For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
# RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
# USER appuser

# # During debugging, this entry point will be overridden. 
# For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["gunicorn", "--bind", "0.0.0.0:2020", "-k", "uvicorn.workers.UvicornWorker", "api.main:app"] 