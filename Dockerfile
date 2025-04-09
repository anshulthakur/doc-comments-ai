FROM python:3.10

FROM python:3.12.6-slim-bookworm

# Set environment variables
ENV PYTHONFAULTHANDLER=1 \
PYTHONUNBUFFERED=1 \
PYTHONHASHSEED=random \
PIP_NO_CACHE_DIR=off \
PIP_DISABLE_PIP_VERSION_CHECK=on \
PIP_DEFAULT_TIMEOUT=100 \
POETRY_NO_INTERACTION=1 \
POETRY_VIRTUALENVS_CREATE=false \
POETRY_CACHE_DIR='/var/cache/pypoetry' \
POETRY_HOME='/usr/local' \
POETRY_VERSION=1.8.3

# Install Poetry
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN curl -sSL https://install.python-poetry.org | python3 -

# Set the working directory
WORKDIR /app

# Copy the pyproject.toml and poetry.lock files
COPY pyproject.toml poetry.lock /app/

# Install dependencies
RUN poetry install --no-ansi $(test "$ENVIRONMENT" == production && echo "--only=main")

# Copy the rest of the application code
COPY ./doc_comments_ai /app

# Command to run the application
CMD ["python3", "main.py"]