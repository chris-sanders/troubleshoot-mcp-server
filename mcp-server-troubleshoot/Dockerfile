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

# Install Python dependencies and make sure entry points are installed
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir -e .

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
    file \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl (select the correct architecture for the container)
RUN curl -LO "https://dl.k8s.io/release/stable.txt" && \
    KUBECTL_VERSION=$(cat stable.txt) && \
    ARCH=$(uname -m) && \
    if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then \
        curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/arm64/kubectl"; \
    else \
        curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"; \
    fi && \
    chmod +x kubectl && \
    mv kubectl /usr/local/bin/ && \
    rm stable.txt

# Create a mock sbctl script for testing
RUN mkdir -p /usr/local/bin && \
    echo '#!/bin/bash' > /usr/local/bin/sbctl && \
    echo '# Mock sbctl script that simulates functionality for testing' >> /usr/local/bin/sbctl && \
    echo '# This creates a fake kubeconfig in the current directory' >> /usr/local/bin/sbctl && \
    echo '' >> /usr/local/bin/sbctl && \
    echo 'if [ "$1" = "--version" ]; then' >> /usr/local/bin/sbctl && \
    echo '  echo "sbctl version 0.17.1 (mock for testing)"' >> /usr/local/bin/sbctl && \
    echo '  exit 0' >> /usr/local/bin/sbctl && \
    echo 'fi' >> /usr/local/bin/sbctl && \
    echo '' >> /usr/local/bin/sbctl && \
    echo 'if [ "$1" = "serve" ]; then' >> /usr/local/bin/sbctl && \
    echo '  # Check for the support bundle location' >> /usr/local/bin/sbctl && \
    echo '  BUNDLE_LOCATION=""' >> /usr/local/bin/sbctl && \
    echo '  for i in $(seq 1 $#); do' >> /usr/local/bin/sbctl && \
    echo '    if [ "${!i}" = "--support-bundle-location" ]; then' >> /usr/local/bin/sbctl && \
    echo '      next=$((i+1))' >> /usr/local/bin/sbctl && \
    echo '      BUNDLE_LOCATION="${!next}"' >> /usr/local/bin/sbctl && \
    echo '      break' >> /usr/local/bin/sbctl && \
    echo '    fi' >> /usr/local/bin/sbctl && \
    echo '  done' >> /usr/local/bin/sbctl && \
    echo '' >> /usr/local/bin/sbctl && \
    echo '  if [ -z "$BUNDLE_LOCATION" ]; then' >> /usr/local/bin/sbctl && \
    echo '    echo "Error: No support bundle location specified"' >> /usr/local/bin/sbctl && \
    echo '    exit 1' >> /usr/local/bin/sbctl && \
    echo '  fi' >> /usr/local/bin/sbctl && \
    echo '' >> /usr/local/bin/sbctl && \
    echo '  if [ ! -f "$BUNDLE_LOCATION" ]; then' >> /usr/local/bin/sbctl && \
    echo '    echo "Error: Support bundle file not found at $BUNDLE_LOCATION"' >> /usr/local/bin/sbctl && \
    echo '    exit 1' >> /usr/local/bin/sbctl && \
    echo '  fi' >> /usr/local/bin/sbctl && \
    echo '' >> /usr/local/bin/sbctl && \
    echo '  # Create a mock kubeconfig file' >> /usr/local/bin/sbctl && \
    echo '  cat > ./kubeconfig << EOF' >> /usr/local/bin/sbctl && \
    echo 'apiVersion: v1' >> /usr/local/bin/sbctl && \
    echo 'kind: Config' >> /usr/local/bin/sbctl && \
    echo 'clusters:' >> /usr/local/bin/sbctl && \
    echo '- cluster:' >> /usr/local/bin/sbctl && \
    echo '    server: http://localhost:8080' >> /usr/local/bin/sbctl && \
    echo '  name: mock-cluster' >> /usr/local/bin/sbctl && \
    echo 'contexts:' >> /usr/local/bin/sbctl && \
    echo '- context:' >> /usr/local/bin/sbctl && \
    echo '    cluster: mock-cluster' >> /usr/local/bin/sbctl && \
    echo '    user: mock-user' >> /usr/local/bin/sbctl && \
    echo '  name: mock-context' >> /usr/local/bin/sbctl && \
    echo 'current-context: mock-context' >> /usr/local/bin/sbctl && \
    echo 'users:' >> /usr/local/bin/sbctl && \
    echo '- name: mock-user' >> /usr/local/bin/sbctl && \
    echo '  user: {}' >> /usr/local/bin/sbctl && \
    echo 'EOF' >> /usr/local/bin/sbctl && \
    echo '' >> /usr/local/bin/sbctl && \
    echo '  # Print some startup info' >> /usr/local/bin/sbctl && \
    echo '  echo "Starting mock sbctl server with support bundle: $BUNDLE_LOCATION"' >> /usr/local/bin/sbctl && \
    echo '  echo "Created kubeconfig at ./kubeconfig"' >> /usr/local/bin/sbctl && \
    echo '' >> /usr/local/bin/sbctl && \
    echo '  # Keep running to simulate the server' >> /usr/local/bin/sbctl && \
    echo '  tail -f /dev/null' >> /usr/local/bin/sbctl && \
    echo 'else' >> /usr/local/bin/sbctl && \
    echo '  echo "Unknown command: $1"' >> /usr/local/bin/sbctl && \
    echo '  echo "Usage: sbctl serve --support-bundle-location <path>"' >> /usr/local/bin/sbctl && \
    echo '  exit 1' >> /usr/local/bin/sbctl && \
    echo 'fi' >> /usr/local/bin/sbctl && \
    chmod +x /usr/local/bin/sbctl && \
    /usr/local/bin/sbctl --version

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