FROM python:3.11-slim

WORKDIR /app

# Install minimal dependencies for the example
RUN pip install --no-cache-dir mcp>=1.6.0 pydantic>=2.0.0

# Copy only the example file
COPY stdio_lifecycle_example.py .

# CRITICAL: Disable output buffering for reliable stdio communication
ENV PYTHONUNBUFFERED=1

# The example will be run via the demonstration script
CMD ["python", "stdio_lifecycle_example.py"]