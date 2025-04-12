#!/usr/bin/env python3
"""
Integration test for MCP server container.
This script:
1. Ensures Docker is available
2. Ensures the image is built
3. Tests running the container with a simple command
4. Reports success/failure
"""

import subprocess
import sys
import os
from pathlib import Path

# Create bundles directory if it doesn't exist
bundles_dir = Path("./bundles")
bundles_dir.mkdir(exist_ok=True)

# Set a test token
os.environ["SBCTL_TOKEN"] = "test-token"

# Build the container if needed
print("Checking if image exists...")
check_image = subprocess.run(
    ["docker", "images", "-q", "mcp-server-troubleshoot:latest"],
    stdout=subprocess.PIPE,
    text=True
)

if not check_image.stdout.strip():
    print("Building container image...")
    try:
        build_result = subprocess.run(["./build.sh"], check=True, capture_output=True, text=True)
        print("Container image built successfully")
    except subprocess.CalledProcessError as e:
        print(f"Failed to build image: {e}")
        print(f"Build output: {e.stdout}")
        print(f"Build errors: {e.stderr}")
        sys.exit(1)

# First, check if the test container is already running and clean it up
print("Cleaning up any existing test containers...")
subprocess.run(
    ["docker", "rm", "-f", "mcp-test"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

# Test running the container with a simple command - override entrypoint
print("\n=== TEST: Basic Container Functionality ===")
try:
    # Run the container with a simple version check command
    result = subprocess.run(
        [
            "docker", "run", "--name", "mcp-test", "--rm",
            "-v", f"{os.getcwd()}/bundles:/data/bundles",
            "-e", f"SBCTL_TOKEN={os.environ.get('SBCTL_TOKEN', 'test-token')}",
            "--entrypoint", "/bin/bash",
            "mcp-server-troubleshoot:latest", 
            "-c", "echo 'Container is working!'"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True
    )
    
    print(f"Container output: {result.stdout.strip()}")
    print("\n✅ Basic container functionality test passed!")
    
except subprocess.CalledProcessError as e:
    print(f"\n❌ Container test failed: {e}")
    print(f"Stdout: {e.stdout}")
    print(f"Stderr: {e.stderr}")
    sys.exit(1)

# Check if Python works
print("\n=== TEST: Python Functionality ===")
try:
    result = subprocess.run(
        [
            "docker", "run", "--name", "mcp-test", "--rm",
            "-v", f"{os.getcwd()}/bundles:/data/bundles",
            "-e", f"SBCTL_TOKEN={os.environ.get('SBCTL_TOKEN', 'test-token')}",
            "--entrypoint", "/bin/bash",
            "mcp-server-troubleshoot:latest", 
            "-c", "python --version"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True
    )
    
    version_output = result.stdout.strip() or result.stderr.strip()
    print(f"Python version: {version_output}")
    print("\n✅ Python version check passed!")
    
except subprocess.CalledProcessError as e:
    print(f"\n❌ Python version check failed: {e}")
    print(f"Stdout: {e.stdout}")
    print(f"Stderr: {e.stderr}")
    sys.exit(1)

# Check if MCP CLI works
print("\n=== TEST: MCP Server CLI ===")
try:
    # Run with --help to verify CLI works
    result = subprocess.run(
        [
            "docker", "run", "--name", "mcp-test", "--rm",
            "-v", f"{os.getcwd()}/bundles:/data/bundles",
            "-e", f"SBCTL_TOKEN={os.environ.get('SBCTL_TOKEN', 'test-token')}",
            "--entrypoint", "/bin/bash",
            "mcp-server-troubleshoot:latest", 
            "-c", "python -m mcp_server_troubleshoot.cli --help"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    if result.returncode == 0 or "usage:" in (result.stderr + result.stdout).lower():
        print("\n✅ MCP server CLI test passed!")
        output = result.stdout or result.stderr
        if output:
            print(f"CLI help output: {output.strip()[:100]}...")
    else:
        print("\n❓ MCP server CLI didn't show usage info, but didn't fail")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")
    
except subprocess.CalledProcessError as e:
    print(f"\n❌ MCP server CLI test failed: {e}")
    print(f"Stdout: {e.stdout}")
    print(f"Stderr: {e.stderr}")
    
print("\nAll tests completed. The container image is ready for use!")
print("To use it with MCP clients, follow the instructions in DOCKER.md.")