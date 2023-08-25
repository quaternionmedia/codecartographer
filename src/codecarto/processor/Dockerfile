# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.11-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
COPY /src/codecarto/processor/requirements_processor.txt .
RUN python -m pip install -r requirements_processor.txt

# Directory
# WORKDIR /processor
# COPY ./src/codecarto/processor /processor

COPY ./src/codecarto/processor .

# # Creates a non-root user with an explicit UID and adds permission to access the /codecarto folder
# RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /codecarto
# USER appuser

# CMD ["python", "codecarto.py"]