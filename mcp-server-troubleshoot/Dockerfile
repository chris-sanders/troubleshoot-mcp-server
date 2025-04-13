FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for Python package management
RUN pip install --no-cache-dir uv

# Set up working directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies including optional ones
RUN pip install --no-cache-dir -e ".[all]" && \
    pip install --no-cache-dir -e ".[all]"

# Second stage for runtime
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PATH="/usr/local/bin:${PATH}" \
    MAX_INITIALIZATION_TIMEOUT=180 \
    MAX_DOWNLOAD_TIMEOUT=120 \
    SBCTL_CLEANUP_ORPHANED=true \
    SBCTL_ALLOW_ALTERNATIVE_KUBECONFIG=true

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    apt-transport-https \
    gnupg \
    file \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl
RUN curl -LO "https://dl.k8s.io/release/stable.txt" && \
    KUBECTL_VERSION=$(cat stable.txt) && \
    curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && \
    mv kubectl /usr/local/bin/ && \
    rm stable.txt

# Install the real sbctl binary - AMD64 version for standard container usage
RUN mkdir -p /tmp/sbctl && cd /tmp/sbctl && \
    curl -L -o sbctl.tar.gz "https://github.com/replicatedhq/sbctl/releases/latest/download/sbctl_linux_amd64.tar.gz" && \
    tar xzf sbctl.tar.gz && \
    chmod +x sbctl && \
    mv sbctl /usr/local/bin/ && \
    cd / && \
    rm -rf /tmp/sbctl && \
    sbctl --help

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

# Command to run - use ENTRYPOINT + CMD pattern for flexibility
# This allows overriding the command while keeping the entrypoint
ENTRYPOINT ["python"]
CMD ["-m", "mcp_server_troubleshoot"]