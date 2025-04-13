#!/bin/bash
set -e

# Configuration
IMAGE_NAME="mcp-server-troubleshoot"
CONTAINER_NAME="mcp-stdio-lifecycle-demo"

echo "=== MCP Server Stdio Lifecycle Demonstration ==="

# Build the Docker image
echo "Building Docker image..."
./scripts/build.sh

# Remove existing container if it exists
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Removing existing container..."
    docker rm -f $CONTAINER_NAME
fi

# Create a simple test script to run in the container
cat > /tmp/test_lifecycle.sh << 'EOF'
#!/bin/bash
set -e

# Start the server in the background with stdio mode
echo "Starting server in background with stdio mode..."
python -m mcp_server_troubleshoot.cli --use-stdio --verbose --enable-periodic-cleanup > /tmp/server.out 2> /tmp/server.log &
SERVER_PID=$!

# Wait for server to initialize
sleep 2
echo "Server started with PID: $SERVER_PID"

# Send a test request
echo -e "\n--- SENDING TEST REQUEST ---"
echo '{"jsonrpc": "2.0", "id": 1, "method": "list_available_bundles", "params": {}}' > /tmp/request.json
cat /tmp/request.json | python -c '
import sys, json
request = json.loads(sys.stdin.read())
print(json.dumps(request))
' > /proc/$SERVER_PID/fd/0

sleep 1

# Check for response in output
echo -e "\n--- SERVER RESPONSE ---"
cat /tmp/server.out | head -n 2 || echo "No response found"

# Send SIGTERM to trigger shutdown
echo -e "\n--- SENDING SIGTERM TO TRIGGER SHUTDOWN ---"
kill -TERM $SERVER_PID

# Wait for shutdown to complete
sleep 2

# Check for temp directories in logs
echo -e "\n--- CHECKING TEMP DIRECTORY CREATION AND CLEANUP ---"
grep -i "Created temporary directory" /tmp/server.log || echo "No temp directory creation log found"
grep -i "Removing temporary directory" /tmp/server.log || echo "No temp directory cleanup log found"

# Show the server logs
echo -e "\n--- SERVER LOGS ---"
echo "=== STARTUP LOGS ==="
grep -i "starting\|startup" /tmp/server.log || echo "No startup logs found"

echo -e "\n=== RESOURCE CREATION LOGS ==="
grep -i "created\|temporary\|resource\|initialize" /tmp/server.log || echo "No resource creation logs found"

echo -e "\n=== SHUTDOWN LOGS ==="
grep -i "shutting\|shutdown\|removing\|cleanup\|cancel" /tmp/server.log || echo "No shutdown logs found"

echo -e "\n=== UPTIME CALCULATION ==="
grep -i "running for" /tmp/server.log || echo "No uptime calculation found"

echo -e "\n--- TEST COMPLETE ---"
EOF

chmod +x /tmp/test_lifecycle.sh

# Run the container with the test script
echo "Running test in container..."
docker run --name $CONTAINER_NAME \
    -v "/tmp/test_lifecycle.sh:/app/test_lifecycle.sh" \
    $IMAGE_NAME /app/test_lifecycle.sh

# Clean up
echo -e "\n=== Cleaning up ==="
docker rm $CONTAINER_NAME > /dev/null 2>&1 || true
rm -f /tmp/test_lifecycle.sh

echo -e "\n=== Demonstration complete ==="