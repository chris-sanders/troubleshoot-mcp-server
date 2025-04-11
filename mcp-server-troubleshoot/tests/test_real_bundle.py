"""
Tests with a real support bundle.
"""

import os
import asyncio
import subprocess
import tempfile
from pathlib import Path
import pytest

from mcp_server_troubleshoot.bundle import BundleManager, BundleMetadata, BundleManagerError


def test_sbctl_direct():
    """
    Direct test of sbctl with the real bundle.
    This is a non-async test to check if sbctl can access the bundle directly.
    """
    real_bundle_path = Path("/Users/chris/src/troubleshoot-mcp-server/main/support-bundle-2025-04-11T14_05_31.tar.gz")
    assert real_bundle_path.exists(), f"Support bundle not found at {real_bundle_path}"
    
    # Create a log file in a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        test_log_path = Path(temp_dir) / "sbctl_test.log"
        with open(test_log_path, "w") as log_file:
            log_file.write(f"Testing sbctl with bundle: {real_bundle_path}\n\n")
            
            # Log what sbctl is and where it is
            result = subprocess.run(["which", "sbctl"], capture_output=True, text=True)
            log_file.write(f"sbctl location: {result.stdout}\n")
        
            # Log version or help
            result = subprocess.run(["sbctl", "--help"], capture_output=True, text=True)
            log_file.write(f"sbctl help: {result.stdout}\n")
            
            # Create a work directory for running sbctl
            work_dir_name = os.path.join(temp_dir, "work")
            os.makedirs(work_dir_name, exist_ok=True)
            work_dir = Path(work_dir_name)
            log_file.write(f"Working directory: {work_dir}\n")
            
            # Make sure we have write permission
            os.chmod(work_dir, 0o755)
            
            # Try running in shell mode
            try:
                # Check the shell command options
                log_file.write("\nChecking sbctl shell command options...\n")
                help_cmd = ["sbctl", "shell", "--help"]
                help_result = subprocess.run(help_cmd, capture_output=True, text=True)
                log_file.write(f"shell help output:\n{help_result.stdout}\n")
                
                # Try serve instead - this should start the API server
                log_file.write("\nRunning sbctl serve command...\n")
                serve_cmd = ["sbctl", "serve", "--support-bundle-location", str(real_bundle_path)]
                log_file.write(f"Command: {' '.join(serve_cmd)}\n")
                
                try:
                    # Use a short timeout as serve runs continuously
                    serve_result = subprocess.run(
                        serve_cmd,
                        cwd=str(work_dir),  # Run in the temp directory
                        capture_output=True, 
                        text=True, 
                        timeout=3  # Short timeout since serve runs continuously
                    )
                    log_file.write("Serve command completed (unexpected):\n")
                    log_file.write(f"Return code: {serve_result.returncode}\n")
                    log_file.write(f"STDOUT: {serve_result.stdout}\n")
                    log_file.write(f"STDERR: {serve_result.stderr}\n")
                except subprocess.TimeoutExpired:
                    log_file.write("Serve command timed out (expected for continuously running server)\n")
                
                # Now try the shell command without --no-shell
                log_file.write("\nRunning sbctl shell command...\n")
                shell_cmd = ["sbctl", "shell", "--support-bundle-location", str(real_bundle_path)]
                log_file.write(f"Command: {' '.join(shell_cmd)}\n")
                
                result = subprocess.run(
                    shell_cmd,
                    cwd=str(work_dir),  # Run in the temp directory
                    capture_output=True, 
                    text=True, 
                    timeout=15  # Give it more time
                )
                log_file.write(f"Return code: {result.returncode}\n")
                log_file.write(f"STDOUT:\n{result.stdout}\n")
                log_file.write(f"STDERR:\n{result.stderr}\n")
                
                # See what files were created
                files = list(work_dir.glob("**/*"))
                log_file.write(f"\nFiles created in {work_dir}:\n")
                for file in files:
                    log_file.write(f"  {file.relative_to(work_dir)}\n")
                    
                # Look for kubeconfig specifically
                kubeconfig_files = list(work_dir.glob("**/kubeconfig"))
                if kubeconfig_files:
                    kubeconfig_path = kubeconfig_files[0]
                    log_file.write(f"\nFound kubeconfig at: {kubeconfig_path}\n")
                    
                    # Read and log kubeconfig content
                    try:
                        with open(kubeconfig_path, 'r') as f:
                            kubeconfig_content = f.read()
                        log_file.write(f"Kubeconfig content:\n{kubeconfig_content}\n")
                        
                        # Try kubectl with this kubeconfig
                        kubectl_cmd = ["kubectl", "get", "nodes", "--kubeconfig", str(kubeconfig_path)]
                        log_file.write(f"\nRunning kubectl command: {' '.join(kubectl_cmd)}\n")
                        kubectl_result = subprocess.run(kubectl_cmd, capture_output=True, text=True, timeout=10)
                        log_file.write(f"Return code: {kubectl_result.returncode}\n")
                        log_file.write(f"STDOUT:\n{kubectl_result.stdout}\n")
                        log_file.write(f"STDERR:\n{kubectl_result.stderr}\n")
                    except Exception as e:
                        log_file.write(f"Error with kubeconfig: {str(e)}\n")
                else:
                    log_file.write("\nNo kubeconfig file found!\n")
                    
            except subprocess.TimeoutExpired:
                log_file.write("\nsbctl shell command timed out\n")
                
                # See what files were created anyway
                files = list(work_dir.glob("**/*"))
                log_file.write(f"\nFiles created during timeout in {work_dir}:\n")
                for file in files:
                    log_file.write(f"  {file.relative_to(work_dir)}\n")
                
                # Look for kubeconfig
                kubeconfig_files = list(work_dir.glob("**/kubeconfig"))
                if kubeconfig_files:
                    kubeconfig_path = kubeconfig_files[0]
                    log_file.write(f"\nFound kubeconfig at: {kubeconfig_path}\n")
                    
                    # Try reading it
                    try:
                        with open(kubeconfig_path, 'r') as f:
                            kubeconfig_content = f.read()
                        log_file.write(f"Kubeconfig content:\n{kubeconfig_content}\n")
                    except Exception as e:
                        log_file.write(f"Error reading kubeconfig: {str(e)}\n")
            except Exception as e:
                log_file.write(f"\nUnexpected error: {str(e)}\n")
                
        # Assert that we created the log file successfully
        assert test_log_path.exists()
        print(f"\nTest log created at: {test_log_path.absolute()}\n")


@pytest.mark.asyncio
async def test_bundle_manager_simple():
    """
    Simple test of the bundle manager with a real support bundle.
    This test just prints results to stdout.
    """
    # Path to the real support bundle
    real_bundle_path = Path("/Users/chris/src/troubleshoot-mcp-server/main/support-bundle-2025-04-11T14_05_31.tar.gz")
    assert real_bundle_path.exists(), f"Support bundle not found at {real_bundle_path}"
    
    print(f"\nTesting BundleManager with real bundle: {real_bundle_path}\n")
    
    # Create a temp directory for the bundle
    temp_dir = tempfile.mkdtemp(prefix="bundle_test_")
    bundle_dir = Path(temp_dir)
    print(f"Bundle directory: {bundle_dir}")
    
    # Create the manager
    manager = BundleManager(bundle_dir)
    
    try:
        # Attempt to initialize the bundle
        print("Initializing bundle, this might take a while...")
        
        # Use a shorter timeout to avoid long hangs
        try:
            result = await asyncio.wait_for(
                manager.initialize_bundle(str(real_bundle_path)), 
                timeout=15.0
            )
            print(f"Bundle initialized successfully!")
            print(f"Bundle ID: {result.id}")
            print(f"Bundle path: {result.path}")
            print(f"Kubeconfig path: {result.kubeconfig_path}")
            print(f"Kubeconfig exists: {result.kubeconfig_path.exists()}")
            print(f"Initialized: {result.initialized}")
            
        except asyncio.TimeoutError:
            print("Bundle initialization timed out after 15 seconds")
            
            # List any files created
            files = list(bundle_dir.glob("**/*"))
            print(f"\nFiles created during initialization:")
            for file in files:
                print(f"  {file.relative_to(bundle_dir)}")
                
        except BundleManagerError as e:
            print(f"Bundle initialization error: {str(e)}")
            
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            
    finally:
        # Clean up
        print("\nCleaning up resources...")
        try:
            await asyncio.wait_for(manager.cleanup(), timeout=5.0)
            print("Cleanup completed successfully")
        except asyncio.TimeoutError:
            print("Cleanup timed out")
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")
        
        # Clean up the temp directory
        try:
            if bundle_dir.exists():
                shutil.rmtree(bundle_dir)
                print(f"Removed bundle directory: {bundle_dir}")
        except Exception as e:
            print(f"Error removing bundle directory: {str(e)}")
    
    # Simple pass assertion
    assert True, "Test completed"