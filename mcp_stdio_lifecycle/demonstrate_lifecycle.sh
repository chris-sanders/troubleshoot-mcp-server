#!/bin/bash
set -e

# Configuration
IMAGE_NAME="mcp-stdio-lifecycle"
CONTAINER_NAME="mcp-stdio-lifecycle"

echo "=== FastMCP Stdio Lifecycle Demonstration ==="

# Build the Docker image
echo "Building Docker image..."
docker build -t $IMAGE_NAME .

# Remove existing container if it exists
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Removing existing container..."
    docker rm -f $CONTAINER_NAME
fi

# Create a simple test script to run in the container
cat > test.sh << 'EOF'
#!/bin/bash
set -e

# Start the server in the background
echo "Starting server in background..."
python stdio_lifecycle_example.py > /tmp/server.out 2> /tmp/server.log &
SERVER_PID=$!

# Wait for server to initialize
sleep 2
echo "Server started with PID: $SERVER_PID"

# Check if the temp file was created
echo -e "\n--- CHECKING RESOURCE CREATION ---"
if [ -f "/app/temp_data.txt" ]; then
    echo "✅ Temp file created: $(cat /app/temp_data.txt)"
else
    echo "❌ Temp file not found"
    ls -la /app
fi

# Send SIGTERM to trigger shutdown
echo -e "\n--- SENDING SIGTERM TO TRIGGER SHUTDOWN ---"
kill -TERM $SERVER_PID

# Wait for shutdown to complete
sleep 2

# Check if the temp file was removed
echo -e "\n--- CHECKING RESOURCE CLEANUP ---"
if [ -f "/app/temp_data.txt" ]; then
    echo "❌ Temp file still exists after shutdown"
else
    echo "✅ Temp file was properly removed during shutdown"
fi

# Show the server logs
echo -e "\n--- SERVER LOGS ---"
echo "=== STARTUP LOGS ==="
grep -i "starting\|startup" /tmp/server.log || echo "No startup logs found"

echo -e "\n=== RESOURCE CREATION LOGS ==="
grep -i "created\|temporary\|resource" /tmp/server.log || echo "No resource creation logs found"

echo -e "\n=== SHUTDOWN LOGS ==="
grep -i "shutting\|shutdown\|removing\|cleanup" /tmp/server.log || echo "No shutdown logs found"

echo -e "\n--- TEST COMPLETE ---"
EOF

chmod +x test.sh

# Run the container with the test script
echo "Running test in container..."
docker run --name $CONTAINER_NAME \
    -v "$(pwd)/test.sh:/app/test.sh" \
    $IMAGE_NAME /app/test.sh

# Clean up
echo -e "\n=== Cleaning up ==="
docker rm $CONTAINER_NAME > /dev/null 2>&1 || true
rm -f test.sh

echo -e "\n=== Demonstration complete ==="