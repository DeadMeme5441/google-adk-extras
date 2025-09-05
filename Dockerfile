# Dockerfile for custom-adk-services
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock README.md MANIFEST.in ./
COPY src/ src/

# Install dependencies and project
RUN uv sync --locked --no-cache

# Expose default ports that might be used by services
EXPOSE 8000 6379 27017 5432

# Default command
CMD ["uv", "run", "python", "-c", "print('Custom ADK Services container is running. Use uv run to execute your application.')"]