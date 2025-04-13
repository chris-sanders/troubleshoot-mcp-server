#!/bin/bash
set -e

# Script to prepare environment for running e2e tests

echo "=== Preparing environment for e2e tests ==="

# Step 1: Build the test Docker image
echo "Building test Docker image with mock sbctl..."
./scripts/build_test.sh

# Step 2: Prepare test fixtures
echo "Preparing test fixtures..."
mkdir -p tests/fixtures/extracted

# Make mock_sbctl.py executable
chmod +x "$(pwd)/tests/fixtures/mock_sbctl.py"

# Step 3: Prepare test support bundle if needed
BUNDLE_PATH="tests/fixtures/support-bundle-2025-04-11T14_05_31.tar.gz"
if [ ! -f "$BUNDLE_PATH" ]; then
    echo "Creating minimal test support bundle..."
    mkdir -p tests/fixtures/tmp_bundle
    # Create minimal bundle structure
    mkdir -p tests/fixtures/tmp_bundle/cluster-info
    mkdir -p tests/fixtures/tmp_bundle/cluster-resources
    mkdir -p tests/fixtures/tmp_bundle/pods
    mkdir -p tests/fixtures/tmp_bundle/logs
    
    # Add some minimal content
    echo "v1.25.0" > tests/fixtures/tmp_bundle/version.txt
    echo "{\"version\": \"v1.25.0\"}" > tests/fixtures/tmp_bundle/cluster-info/version.json
    echo "test-host" > tests/fixtures/tmp_bundle/hostname
    echo "NAME=Ubuntu" > tests/fixtures/tmp_bundle/etc-os-release
    
    # Create bundle tarball
    cd tests/fixtures/tmp_bundle
    tar -czf ../support-bundle-2025-04-11T14_05_31.tar.gz *
    cd ../../..
    rm -rf tests/fixtures/tmp_bundle
    echo "Created test support bundle at $BUNDLE_PATH"
fi

# Step 4: Set up environment variables
echo "Setting up environment variables for testing..."
cat > tests/fixtures/env.sh << 'EOF'
#!/bin/bash
# Environment variables for e2e tests
export MCP_CLIENT_DEBUG=true
export USE_MOCK_SBCTL=true
export MCP_LOG_LEVEL=DEBUG
export MCP_CLIENT_TIMEOUT=10.0
export PATH="$(pwd)/tests/fixtures:$PATH"
EOF
chmod +x tests/fixtures/env.sh

echo "=== Environment prepared for e2e testing ==="
echo "To run e2e tests, use one of the following commands:"
echo "  source tests/fixtures/env.sh && python -m pytest tests/e2e/test_docker.py -v"
echo "  source tests/fixtures/env.sh && python -m pytest tests/e2e/test_container.py -v"
echo ""
echo "To run a specific test with detailed debugging, use:"
echo "  source tests/fixtures/env.sh && python -m pytest tests/e2e/test_container.py::test_basic_container_functionality -v"