FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for Python package management
RUN curl -sSf https://astral.sh/uv/install.sh | sh

# Set up working directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies
RUN ~/.cargo/bin/uv pip install --no-cache-dir -e .

# Second stage for runtime
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/usr/local/bin:${PATH}"

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    apt-transport-https \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl
RUN curl -LO "https://dl.k8s.io/release/stable.txt" && \
    KUBECTL_VERSION=$(cat stable.txt) && \
    curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && \
    mv kubectl /usr/local/bin/ && \
    rm stable.txt

# Install sbctl (this is a placeholder, replace with actual installation instructions)
# For now, we're simulating sbctl with a script
RUN mkdir -p /usr/local/bin && \
    echo '#!/bin/bash\necho "Simulating sbctl with kubeconfig at $2"\nmkdir -p $(dirname $2)\ntouch $2\n' > /usr/local/bin/sbctl && \
    chmod +x /usr/local/bin/sbctl

# Create data directory for bundles
RUN mkdir -p /data/bundles
VOLUME /data/bundles

# Set working directory
WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app /app

# User setup
RUN useradd -m mcp-user && \
    chown -R mcp-user:mcp-user /app /data

USER mcp-user

# Command to run
ENTRYPOINT ["python", "-m", "mcp_server_troubleshoot"]
CMD []