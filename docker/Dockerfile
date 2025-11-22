FROM python:3.13-slim-bookworm

RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    curl \
    libmariadb-dev-compat \
    libmariadb-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ADD https://astral.sh/uv/install.sh /install.sh
RUN chmod -R 755 /install.sh && /install.sh && rm /install.sh

# Verify that uv is installed
RUN which uv || echo "uv not found"

# Set up the UV environment path correctly
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /src

COPY ../ .
COPY tests/ ../tests/

# Correct the PATH configuration
ENV PATH="/src/.venv/bin:${PATH}"

RUN uv sync

# Expose the specified port for FastAPI
EXPOSE $PORT

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
