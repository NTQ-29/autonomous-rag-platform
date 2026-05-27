# 1. Use a lightweight, official Python runtime base image
FROM python:3.12-slim

# 2. Set system environment configurations
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# 3. Establish the secure working directory inside the container
WORKDIR /app

# 4. Install system dependencies required for heavy parsing extensions if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 5. Copy over the environment configuration manifest first to leverage Docker caching
COPY requirements.txt .

# 6. Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 7. Copy the application source files into the container image
COPY ingestor.py graph_nodes.py schemas.py mcp_server.py ./

# 8. Expose the networking port used by the streamable-http transport layer
EXPOSE 8000

# 9. Execute the MCP Server application on startup
CMD ["python", "mcp_server.py"]
