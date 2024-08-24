FROM tiangolo/uvicorn-gunicorn:python3.11 

EXPOSE 2020 

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install Jupyter Notebook and create a kernel for Python 3
RUN pip install jupyter
RUN python -m ipykernel install --user --name python3

# Install pip requirements
COPY ./src/codecarto/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
        python -m pip install -r requirements.txt

# Directory
WORKDIR /app
COPY ./graphbase /app/graphbase
RUN --mount=type=cache,target=/root/.cache/pip \
        python -m pip install -e /app/graphbase
COPY ./src/codecarto /app
ENV PYTHONPATH=/app

# # Creates a non-root user with an explicit UID and adds permission to access the /app folder
# RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
# USER appuser
# # Good idea to also remove the shell access and ensure there is no home directory for the user
# RUN addgroup --gid 1001 --system app && \
#     adduser --no-create-home --shell /bin/false --disabled-password --uid 1001 --system --group app
# USER app
 
# # During debugging, this entry point will be overridden. 
# For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["gunicorn", "--bind", "0.0.0.0:2020", "--timeout", "120", "-k", "uvicorn.workers.UvicornWorker", "main:app"]  