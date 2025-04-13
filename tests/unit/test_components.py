#!/usr/bin/env python3
"""
Standalone component test for the MCP server.

This script directly tests the key components without relying on the MCP protocol.
"""

import pytest
import pytest_asyncio

# Mark all tests in this file as unit tests
pytestmark = pytest.mark.unit

import argparse
import asyncio
import json
import logging
import os
import sys
import tempfile
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("test_components")

# Path to the test fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"
TEST_BUNDLE = FIXTURES_DIR / "support-bundle-2025-04-11T14_05_31.tar.gz"


@pytest.mark.asyncio
async def test_bundle_initialization():
    """Test bundle initialization."""
    from mcp_server_troubleshoot.bundle import BundleManager
    
    logger.info("Testing bundle initialization")
    
    # Create a temporary directory for bundle storage
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_bundle_dir = Path(temp_dir)
        logger.info(f"Created temporary directory: {temp_bundle_dir}")
        
        # Set up mock sbctl and kubectl
        mock_sbctl_path = FIXTURES_DIR / "mock_sbctl.py"
        mock_kubectl_path = FIXTURES_DIR / "mock_kubectl.py"
        temp_bin_dir = temp_bundle_dir / "bin"
        temp_bin_dir.mkdir(exist_ok=True)
        
        # Create sbctl mock
        sbctl_link = temp_bin_dir / "sbctl"
        logger.info(f"Creating mock sbctl at: {sbctl_link}")
        with open(sbctl_link, "w") as f:
            f.write(f"""#!/bin/bash
python "{mock_sbctl_path}" "$@"
""")
        os.chmod(sbctl_link, 0o755)
        
        # Create kubectl mock (though not used in this test, for consistency)
        kubectl_link = temp_bin_dir / "kubectl"
        logger.info(f"Creating mock kubectl at: {kubectl_link}")
        with open(kubectl_link, "w") as f:
            f.write(f"""#!/bin/bash
python "{mock_kubectl_path}" "$@"
""")
        os.chmod(kubectl_link, 0o755)
        
        # Add our mock tools to the PATH
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{temp_bin_dir}:{old_path}"
        
        # Copy the test bundle if it exists
        if TEST_BUNDLE.exists():
            import shutil
            test_bundle_copy = temp_bundle_dir / TEST_BUNDLE.name
            shutil.copy(TEST_BUNDLE, test_bundle_copy)
            logger.info(f"Copied test bundle to: {test_bundle_copy}")
        else:
            logger.warning("Test bundle not found")
            return False
        
        # Create a bundle manager
        bundle_manager = BundleManager(temp_bundle_dir)
        logger.info("Created bundle manager")
        
        try:
            # Initialize the bundle
            logger.info("Initializing bundle...")
            metadata = await bundle_manager.initialize_bundle(str(test_bundle_copy), force=True)
            logger.info(f"Bundle initialized: {metadata.id}")
            logger.info(f"  Path: {metadata.path}")
            logger.info(f"  Kubeconfig: {metadata.kubeconfig_path}")
            logger.info(f"  Initialized: {metadata.initialized}")
            
            # Check if kubeconfig exists
            if metadata.kubeconfig_path.exists():
                logger.info("Kubeconfig file exists")
            else:
                logger.error("Kubeconfig file does not exist")
                return False
            
            # Get diagnostic information
            diagnostics = await bundle_manager.get_diagnostic_info()
            logger.info("Bundle diagnostic information:")
            logger.info(f"  sbctl available: {diagnostics['sbctl_available']}")
            logger.info(f"  sbctl process running: {diagnostics['sbctl_process_running']}")
            logger.info(f"  API server available: {diagnostics['api_server_available']}")
            logger.info(f"  Bundle initialized: {diagnostics['bundle_initialized']}")
            
            # Check if bundle is initialized
            if not metadata.initialized:
                logger.error("Bundle not marked as initialized")
                return False
            
            # Check if API server is available
            if not diagnostics['api_server_available']:
                logger.error("API server not available")
                return False
            
            # Clean up the bundle manager before exiting
            await bundle_manager.cleanup()
            
            return True
            
        except Exception as e:
            logger.exception(f"Error during bundle initialization: {e}")
            try:
                await bundle_manager.cleanup()
            except Exception:
                pass
            return False
        finally:
            # Restore the PATH
            os.environ["PATH"] = old_path


@pytest.mark.asyncio
async def test_kubectl():
    """Test kubectl command execution."""
    from mcp_server_troubleshoot.bundle import BundleManager
    from mcp_server_troubleshoot.kubectl import KubectlExecutor
    
    logger.info("Testing kubectl execution")
    
    # Create a temporary directory for bundle storage
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_bundle_dir = Path(temp_dir)
        logger.info(f"Created temporary directory: {temp_bundle_dir}")
        
        # Set up mock sbctl and kubectl
        mock_sbctl_path = FIXTURES_DIR / "mock_sbctl.py"
        mock_kubectl_path = FIXTURES_DIR / "mock_kubectl.py"
        temp_bin_dir = temp_bundle_dir / "bin"
        temp_bin_dir.mkdir(exist_ok=True)
        
        # Create sbctl mock
        sbctl_link = temp_bin_dir / "sbctl"
        logger.info(f"Creating mock sbctl at: {sbctl_link}")
        with open(sbctl_link, "w") as f:
            f.write(f"""#!/bin/bash
python "{mock_sbctl_path}" "$@"
""")
        os.chmod(sbctl_link, 0o755)
        
        # Create kubectl mock 
        kubectl_link = temp_bin_dir / "kubectl"
        logger.info(f"Creating mock kubectl at: {kubectl_link}")
        with open(kubectl_link, "w") as f:
            f.write(f"""#!/bin/bash
python "{mock_kubectl_path}" "$@"
""")
        os.chmod(kubectl_link, 0o755)
        
        # Add our mock tools to the PATH
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{temp_bin_dir}:{old_path}"
        
        # Copy the test bundle if it exists
        if TEST_BUNDLE.exists():
            import shutil
            test_bundle_copy = temp_bundle_dir / TEST_BUNDLE.name
            shutil.copy(TEST_BUNDLE, test_bundle_copy)
            logger.info(f"Copied test bundle to: {test_bundle_copy}")
        else:
            logger.warning("Test bundle not found")
            return False
        
        # Create a bundle manager and kubectl executor
        bundle_manager = BundleManager(temp_bundle_dir)
        kubectl_executor = KubectlExecutor(bundle_manager)
        logger.info("Created bundle manager and kubectl executor")
        
        try:
            # Initialize the bundle
            logger.info("Initializing bundle...")
            metadata = await bundle_manager.initialize_bundle(str(test_bundle_copy), force=True)
            logger.info(f"Bundle initialized: {metadata.id}")
            
            # Check if the API server is available
            diagnostics = await bundle_manager.get_diagnostic_info()
            logger.info("Bundle diagnostic information:")
            logger.info(f"  sbctl available: {diagnostics['sbctl_available']}")
            logger.info(f"  sbctl process running: {diagnostics['sbctl_process_running']}")
            logger.info(f"  API server available: {diagnostics['api_server_available']}")
            logger.info(f"  Bundle initialized: {diagnostics['bundle_initialized']}")
            
            # Get more detailed API server info
            for key, value in diagnostics.get('system_info', {}).items():
                if key.startswith('port_') or key.startswith('curl_'):
                    logger.info(f"  {key}: {value}")
            
            # Verify all our prerequisites
            if not diagnostics['api_server_available']:
                logger.error("API server is not available, kubectl commands will fail")
                return False
                
            if not metadata.kubeconfig_path.exists():
                logger.error("Kubeconfig file does not exist")
                return False
                
            # Test that we can reach the API server directly
            api_port = None
            try:
                with open(metadata.kubeconfig_path, "r") as f:
                    config = json.load(f)
                if config.get("clusters") and len(config["clusters"]) > 0:
                    server_url = config["clusters"][0]["cluster"].get("server", "")
                    if ":" in server_url:
                        api_port = int(server_url.split(":")[-1])
                        logger.info(f"Extracted API server port from kubeconfig: {api_port}")
            except Exception as e:
                logger.warning(f"Failed to parse kubeconfig: {e}")
            
            # Verify kubectl is available
            try:
                logger.info("Checking if kubectl is in PATH")
                proc = await asyncio.create_subprocess_exec(
                    "which", "kubectl",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                
                if proc.returncode == 0 and stdout:
                    kubectl_path = stdout.decode().strip()
                    logger.info(f"kubectl found at: {kubectl_path}")
                else:
                    logger.error("kubectl not found in PATH")
                    return False
            except Exception as e:
                logger.error(f"Error checking kubectl availability: {e}")
                return False
            
            # Set KUBECONFIG environment variable manually to debug
            os.environ["KUBECONFIG"] = str(metadata.kubeconfig_path)
            logger.info(f"Set KUBECONFIG environment variable to: {os.environ.get('KUBECONFIG')}")
                
            # Try a kubectl command with reduced timeouts and more debugging
            logger.info("Executing kubectl command using simple subprocess first to debug")
            try:
                proc = await asyncio.create_subprocess_exec(
                    "kubectl", "version", "--client",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=os.environ
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
                logger.info(f"kubectl version --client returned {proc.returncode}")
                logger.info(f"stdout: {stdout.decode()[:500] if stdout else 'No output'}")
                logger.info(f"stderr: {stderr.decode()[:500] if stderr else 'No error'}")
            except Exception as e:
                logger.error(f"Error running kubectl version: {e}")
            
            # Now run the intended test command
            logger.info("Executing kubectl command: get nodes (timeout: 10s)")
            try:
                result = await asyncio.wait_for(
                    kubectl_executor.execute("get nodes"), 
                    timeout=10.0
                )
                
                logger.info(f"Command exit code: {result.exit_code}")
                logger.info(f"Duration: {result.duration_ms} ms")
                logger.info(f"Command output: {result.stdout[:500] if result.stdout else 'No output'}")
                
                if result.exit_code != 0:
                    logger.error(f"kubectl command failed: {result.stderr}")
                    return False
                
                logger.info("kubectl test completed successfully")
                return True
            except asyncio.TimeoutError:
                logger.error("kubectl command timed out")
                return False
            finally:
                # Clean up the bundle manager before exiting
                await bundle_manager.cleanup()
            
        except Exception as e:
            logger.exception(f"Error during kubectl test: {e}")
            try:
                await bundle_manager.cleanup()
            except Exception:
                pass
            return False
        finally:
            # Restore the PATH
            os.environ["PATH"] = old_path


@pytest.mark.asyncio
async def test_file_explorer():
    """Test file explorer functionality."""
    from mcp_server_troubleshoot.bundle import BundleManager
    from mcp_server_troubleshoot.files import FileExplorer
    
    logger.info("Testing file explorer")
    
    # Create a temporary directory for bundle storage
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_bundle_dir = Path(temp_dir)
        logger.info(f"Created temporary directory: {temp_bundle_dir}")
        
        # Set up mock sbctl and kubectl
        mock_sbctl_path = FIXTURES_DIR / "mock_sbctl.py"
        mock_kubectl_path = FIXTURES_DIR / "mock_kubectl.py"
        temp_bin_dir = temp_bundle_dir / "bin"
        temp_bin_dir.mkdir(exist_ok=True)
        
        # Create sbctl mock
        sbctl_link = temp_bin_dir / "sbctl"
        logger.info(f"Creating mock sbctl at: {sbctl_link}")
        with open(sbctl_link, "w") as f:
            f.write(f"""#!/bin/bash
python "{mock_sbctl_path}" "$@"
""")
        os.chmod(sbctl_link, 0o755)
        
        # Create kubectl mock (though not used in this test, for consistency)
        kubectl_link = temp_bin_dir / "kubectl"
        logger.info(f"Creating mock kubectl at: {kubectl_link}")
        with open(kubectl_link, "w") as f:
            f.write(f"""#!/bin/bash
python "{mock_kubectl_path}" "$@"
""")
        os.chmod(kubectl_link, 0o755)
        
        # Add our mock tools to the PATH
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{temp_bin_dir}:{old_path}"
        
        # Copy the test bundle if it exists
        if TEST_BUNDLE.exists():
            import shutil
            test_bundle_copy = temp_bundle_dir / TEST_BUNDLE.name
            shutil.copy(TEST_BUNDLE, test_bundle_copy)
            logger.info(f"Copied test bundle to: {test_bundle_copy}")
        else:
            logger.warning("Test bundle not found")
            return False
        
        # Create a bundle manager and file explorer
        bundle_manager = BundleManager(temp_bundle_dir)
        file_explorer = FileExplorer(bundle_manager)
        logger.info("Created bundle manager and file explorer")
        
        try:
            # Initialize the bundle
            logger.info("Initializing bundle...")
            metadata = await bundle_manager.initialize_bundle(str(test_bundle_copy), force=True)
            logger.info(f"Bundle initialized: {metadata.id}")
            
            # Create a sample file for testing
            test_file = metadata.path / "test.txt"
            with open(test_file, "w") as f:
                f.write("This is a test file\nwith multiple lines\nand some content to search.")
            logger.info(f"Created test file: {test_file}")
            
            # Try listing files at the root
            logger.info("Listing files at root directory")
            result = await file_explorer.list_files("/")
            
            logger.info(f"Files found: {result.total_files}, directories found: {result.total_dirs}")
            for entry in result.entries[:5]:  # Show first 5 entries
                logger.info(f"  {entry.type}: {entry.name}")
            
            if result.total_files == 0 and result.total_dirs == 0:
                logger.warning("No files or directories found")
            
            # Try to read the test file
            rel_path = "/test.txt"
            logger.info(f"Reading file: {rel_path}")
            read_result = await file_explorer.read_file(rel_path)
            logger.info(f"File size: {len(read_result.content)} bytes")
            logger.info(f"File content: {read_result.content}")
            
            # Try to search for something in the test file
            logger.info("Searching for 'test'")
            grep_result = await file_explorer.grep_files("test", "/", recursive=True, case_sensitive=False)
            
            logger.info(f"Found {grep_result.total_matches} matches in {grep_result.files_searched} files")
            for match in grep_result.matches[:3]:  # Show first 3 matches
                logger.info(f"  {match.path}:{match.line_number + 1}: {match.line}")
            
            # Clean up the bundle manager before exiting
            await bundle_manager.cleanup()
            
            return True
            
        except Exception as e:
            logger.exception(f"Error during file explorer test: {e}")
            try:
                await bundle_manager.cleanup()
            except Exception:
                pass
            return False
        finally:
            # Restore the PATH
            os.environ["PATH"] = old_path


async def run_tests(tests):
    """Run the specified tests."""
    results = {}
    
    # Create separate environment variables for each test
    # This ensures better isolation between tests
    for test_name in tests:
        # Clear any existing MOCK_K8S_API_PORT environment variable
        if "MOCK_K8S_API_PORT" in os.environ:
            del os.environ["MOCK_K8S_API_PORT"]
            
        # Force the system to find a new port for this test
        logger.info(f"\n=== Clearing all ports before running test: {test_name} ===")
        
        # Add a small sleep to ensure any lingering processes are cleaned up
        await asyncio.sleep(1.0)
        
        if test_name == "bundle":
            logger.info("\n=== Test: Bundle Initialization ===")
            results["bundle"] = await test_bundle_initialization()
        elif test_name == "kubectl":
            logger.info("\n=== Test: Kubectl Execution ===")
            results["kubectl"] = await test_kubectl()
        elif test_name == "files":
            logger.info("\n=== Test: File Explorer ===")
            results["files"] = await test_file_explorer()
        else:
            logger.error(f"Unknown test: {test_name}")
            
        # Add a small delay between tests to ensure port cleanup
        await asyncio.sleep(1.0)
    
    # Print summary
    logger.info("\n=== Test Summary ===")
    all_passed = True
    for test_name, passed in results.items():
        logger.info(f"{test_name}: {'✅' if passed else '❌'}")
        all_passed = all_passed and passed
    
    return all_passed


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Test MCP server components")
    parser.add_argument(
        "--test", 
        choices=["bundle", "kubectl", "files", "all"],
        default="all",
        help="Which component to test (default: all)"
    )
    return parser.parse_args()


async def main():
    """Run all component tests."""
    # Parse command-line arguments
    args = parse_args()
    
    # Set environment variables to speed up tests
    os.environ["MAX_INITIALIZATION_TIMEOUT"] = "10"
    os.environ["MAX_DOWNLOAD_TIMEOUT"] = "10"
    
    # Determine which tests to run
    if args.test == "all":
        tests = ["bundle", "kubectl", "files"]
    else:
        tests = [args.test]
    
    # Run the tests
    return await run_tests(tests)


if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(main())
    sys.exit(0 if success else 1)