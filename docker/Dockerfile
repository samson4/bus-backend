FROM python:3.13-slim-bookworm

RUN apt-get update && apt-get install --no-install-recommends -y \
        build-essential \
        curl && \
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

RUN uv sync

# Correct the PATH configuration
ENV PATH="/src/.venv/bin:${PATH}"

# Expose the specified port for FastAPI
EXPOSE $PORT

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
