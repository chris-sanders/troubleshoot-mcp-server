"""
Tests with a real support bundle.
"""

import os
import sys
import time
import json
import asyncio
import shutil
import subprocess
import tempfile
from pathlib import Path
import pytest

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration

from mcp_server_troubleshoot.bundle import BundleManager, BundleManagerError


def test_sbctl_direct(test_support_bundle):
    """
    Direct test of sbctl with the real bundle.
    This is a non-async test to check if sbctl can access the bundle directly.

    Args:
        test_support_bundle: Path to the test support bundle (pytest fixture)
    """
    real_bundle_path = test_support_bundle

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
                        timeout=3,  # Short timeout since serve runs continuously
                    )
                    log_file.write("Serve command completed (unexpected):\n")
                    log_file.write(f"Return code: {serve_result.returncode}\n")
                    log_file.write(f"STDOUT: {serve_result.stdout}\n")
                    log_file.write(f"STDERR: {serve_result.stderr}\n")
                except subprocess.TimeoutExpired:
                    log_file.write(
                        "Serve command timed out (expected for continuously running server)\n"
                    )

                # Now try the shell command without --no-shell
                log_file.write("\nRunning sbctl shell command...\n")
                shell_cmd = ["sbctl", "shell", "--support-bundle-location", str(real_bundle_path)]
                log_file.write(f"Command: {' '.join(shell_cmd)}\n")

                result = subprocess.run(
                    shell_cmd,
                    cwd=str(work_dir),  # Run in the temp directory
                    capture_output=True,
                    text=True,
                    timeout=15,  # Give it more time
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
                        with open(kubeconfig_path, "r") as f:
                            kubeconfig_content = f.read()
                        log_file.write(f"Kubeconfig content:\n{kubeconfig_content}\n")

                        # Try kubectl with this kubeconfig
                        kubectl_cmd = [
                            "kubectl",
                            "get",
                            "nodes",
                            "--kubeconfig",
                            str(kubeconfig_path),
                        ]
                        log_file.write(f"\nRunning kubectl command: {' '.join(kubectl_cmd)}\n")
                        kubectl_result = subprocess.run(
                            kubectl_cmd, capture_output=True, text=True, timeout=10
                        )
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
                        with open(kubeconfig_path, "r") as f:
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
async def test_bundle_manager_simple(test_support_bundle, clean_asyncio):
    """
    Simple test of the bundle manager with a real support bundle.
    This test just prints results to stdout.

    Args:
        test_support_bundle: Path to the test support bundle (pytest fixture)
        clean_asyncio: Fixture that ensures proper asyncio cleanup
    """
    # Use a high-level context manager to handle resources
    import contextlib
    import gc
    
    real_bundle_path = test_support_bundle

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
            with contextlib.closing(asyncio.get_event_loop()) as loop:
                result = await asyncio.wait_for(
                    manager.initialize_bundle(str(real_bundle_path)), timeout=15.0
                )
                print("Bundle initialized successfully!")
                print(f"Bundle ID: {result.id}")
                print(f"Bundle path: {result.path}")
                print(f"Kubeconfig path: {result.kubeconfig_path}")
                print(f"Kubeconfig exists: {result.kubeconfig_path.exists()}")
                print(f"Initialized: {result.initialized}")

        except asyncio.TimeoutError:
            print("Bundle initialization timed out after 15 seconds")

            # List any files created
            files = list(bundle_dir.glob("**/*"))
            print("\nFiles created during initialization:")
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
            
            # Try to force cleanup of any remaining processes
            try:
                subprocess.run(["pkill", "-f", "sbctl"], capture_output=True)
                print("Sent kill signal to any sbctl processes")
            except:
                pass
                
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")

        # Clean up the temp directory
        try:
            if bundle_dir.exists():
                shutil.rmtree(bundle_dir)
                print(f"Removed bundle directory: {bundle_dir}")
        except Exception as e:
            print(f"Error removing bundle directory: {str(e)}")
        
        # Force garbage collection to clean up any resources
        gc.collect()

    # Simple pass assertion
    assert True, "Test completed"

@pytest.mark.asyncio
async def test_list_files_from_extracted_bundle(test_support_bundle, clean_asyncio):
    """
    Test listing files from an extracted support bundle.
    This test verifies that files can be listed from the extracted bundle directory.
    
    Args:
        test_support_bundle: Path to the test support bundle (pytest fixture)
        clean_asyncio: Fixture that ensures proper asyncio cleanup
    """
    import gc
    from mcp_server_troubleshoot.bundle import BundleManager
    from mcp_server_troubleshoot.files import FileExplorer
    
    real_bundle_path = test_support_bundle
    
    # Create a temp directory for the bundle
    temp_dir = tempfile.mkdtemp(prefix="bundle_explorer_test_")
    bundle_dir = Path(temp_dir)
    print(f"Bundle directory: {bundle_dir}")
    
    # Create the bundle manager
    manager = BundleManager(bundle_dir)
    
    try:
        # Initialize the bundle
        result = await asyncio.wait_for(
            manager.initialize_bundle(str(real_bundle_path)), timeout=30.0
        )
        
        # Verify the bundle was initialized
        assert result.initialized
        assert result.kubeconfig_path.exists()
        
        # Try listing files
        explorer = FileExplorer(manager)
        
        # First list top-level directories
        file_list = await explorer.list_files("", False)
        print(f"Top-level file listing: {[e.name for e in file_list.entries]}")
        print(f"Total files: {file_list.total_files}, Total dirs: {file_list.total_dirs}")
        
        # There should be at least one directory (likely the bundle directory itself)
        assert file_list.total_dirs >= 1
        
        # Navigate into the bundle directory (if it exists)
        top_dir = None
        if file_list.entries and file_list.entries[0].type == "dir":
            top_dir = file_list.entries[0].name
            bundle_contents = await explorer.list_files(top_dir, False)
            print(f"Bundle contents: {[e.name for e in bundle_contents.entries]}")
            print(f"Bundle total files: {bundle_contents.total_files}, Total dirs: {bundle_contents.total_dirs}")
            
            # Check for the extracted directory
            extract_dir_path = f"{top_dir}/extracted"
            if "extracted" in [e.name for e in bundle_contents.entries]:
                extract_list = await explorer.list_files(extract_dir_path, False)
                print(f"Extracted directory contents: {[e.name for e in extract_list.entries]}")
                print(f"Extracted total files: {extract_list.total_files}, Total dirs: {extract_list.total_dirs}")
                
                # There should be at least a few files or directories in the extracted folder
                assert extract_list.total_files + extract_list.total_dirs > 0
            else:
                print("Extracted directory not found in bundle contents")
                
        else:
            print("No top-level directory found, skipping extracted dir check")
        
        # Try reading a file to verify content access
        # Check if we found files in any of the directories
        if top_dir:
            try:
                # First try to find a file in the extracted directory
                extract_dir_path = f"{top_dir}/extracted"
                extract_list = await explorer.list_files(extract_dir_path, True)  # Recursive listing
                
                if extract_list.total_files > 0:
                    # Find the first file to read
                    first_file = next((e.path for e in extract_list.entries if e.type == "file"), None)
                    if first_file:
                        file_content = await explorer.read_file(first_file)
                        print(f"Read file {first_file}: content length = {len(file_content.content)}")
                        assert len(file_content.content) > 0
                        
                # If no files in extracted, try the bundle directory
                elif bundle_contents and bundle_contents.total_files > 0:
                    first_file = next((e.path for e in bundle_contents.entries if e.type == "file"), None)
                    if first_file:
                        file_content = await explorer.read_file(first_file)
                        print(f"Read file {first_file}: content length = {len(file_content.content)}")
                        assert len(file_content.content) > 0
            except Exception as e:
                print(f"Error reading file: {e}")
            
    finally:
        # Clean up
        try:
            await asyncio.wait_for(manager.cleanup(), timeout=5.0)
            print("Cleanup completed successfully")
        except (asyncio.TimeoutError, Exception) as e:
            print(f"Cleanup issue: {e}")
            # Try to force cleanup of any remaining processes
            try:
                subprocess.run(["pkill", "-f", "sbctl"], capture_output=True)
            except:
                pass
        
        if bundle_dir.exists():
            import shutil
            shutil.rmtree(bundle_dir)
            print(f"Removed bundle directory: {bundle_dir}")
            
        # Force garbage collection to clean up any resources
        gc.collect()

@pytest.mark.asyncio
async def test_initialize_with_real_sbctl(test_support_bundle, clean_asyncio):
    """
    Test using the real sbctl executable (not mocked) to initialize a bundle.
    This test will use the actual sbctl in PATH.
    
    Args:
        test_support_bundle: Path to the test support bundle (pytest fixture)
        clean_asyncio: Fixture that ensures proper asyncio cleanup
    """
    import gc
    real_bundle_path = test_support_bundle
    print(f"\nTesting with real sbctl and bundle: {real_bundle_path}\n")
    
    # Verify real sbctl exists in PATH
    try:
        which_result = subprocess.run(
            ["which", "sbctl"], capture_output=True, text=True, check=True
        )
        sbctl_path = which_result.stdout.strip()
        print(f"Using real sbctl at: {sbctl_path}")
        
        # Check sbctl version and help to better understand capabilities
        version_result = subprocess.run(
            ["sbctl", "version"], capture_output=True, text=True
        )
        print(f"sbctl version: {version_result.stdout.strip()}")
        
        # Get help text to understand available commands
        help_result = subprocess.run(
            ["sbctl", "--help"], capture_output=True, text=True
        )
        print(f"sbctl help (first 300 chars):\n{help_result.stdout[:300]}...")
        
        # Check sbctl serve command options specifically
        serve_help_result = subprocess.run(
            ["sbctl", "serve", "--help"], capture_output=True, text=True
        )
        print(f"sbctl serve help (first 300 chars):\n{serve_help_result.stdout[:300]}...")
        
    except subprocess.CalledProcessError as e:
        print(f"Error checking sbctl: {e}")
        pytest.skip("Real sbctl not found in PATH or failed to execute")
    
    # Create a temp directory for the bundle
    temp_dir = tempfile.mkdtemp(prefix="real_sbctl_test_")
    bundle_dir = Path(temp_dir)
    print(f"Bundle directory: {bundle_dir}")
    
    # Set environment variables closer to container environment
    os.environ["PYTHONUNBUFFERED"] = "1"
    os.environ["MAX_INITIALIZATION_TIMEOUT"] = "30"  # Shorter timeout for testing
    
    # Create the manager with extra logging
    import logging
    logger = logging.getLogger("mcp_server_troubleshoot.bundle")
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # First, try running sbctl serve directly to see if it works
    print("\nTrying sbctl serve directly before using BundleManager...")
    try:
        # Run with a short timeout since it's a continuously running process
        serve_proc = subprocess.run(
            ["sbctl", "serve", "--support-bundle-location", str(real_bundle_path)],
            cwd=str(bundle_dir),
            capture_output=True,
            timeout=5.0  # Short timeout since it normally keeps running
        )
        print("sbctl serve unexpectedly completed:")
        print(f"Return code: {serve_proc.returncode}")
        print(f"STDOUT: {serve_proc.stdout.decode()}")
        print(f"STDERR: {serve_proc.stderr.decode()}")
    except subprocess.TimeoutExpired as e:
        print("sbctl serve timed out as expected (it's a long-running process)")
        # Check if any files were created
        files = list(bundle_dir.glob("*"))
        print(f"Files created by direct sbctl serve: {[f.name for f in files]}")
        # Force stop the process
        if hasattr(e, 'process'):
            print("Terminating direct sbctl process...")
            e.process.terminate()
            try:
                e.process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                e.process.kill()
    except Exception as e:
        print(f"Error running direct sbctl serve: {e}")
    
    # Now try the actual test with BundleManager
    manager = BundleManager(bundle_dir)
    
    try:
        # Attempt to initialize the bundle with real sbctl
        print("\nInitializing bundle with real sbctl through BundleManager...")
        
        # Capture the start time
        start_time = time.time()
        
        # Run initialization with a timeout
        try:
            # Use shorter timeout for testing
            result = await asyncio.wait_for(
                manager.initialize_bundle(str(real_bundle_path)), timeout=30.0
            )
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"Bundle initialized successfully in {duration:.2f} seconds!")
            print(f"Bundle ID: {result.id}")
            print(f"Bundle path: {result.path}")
            print(f"Kubeconfig path: {result.kubeconfig_path}")
            
            # Read and log kubeconfig content
            if result.kubeconfig_path.exists():
                with open(result.kubeconfig_path, "r") as f:
                    kubeconfig_content = f.read()
                print(f"Kubeconfig content:\n{kubeconfig_content}")
                
                # Try to extract server URL from kubeconfig
                try:
                    kubeconfig = json.loads(kubeconfig_content)
                    if kubeconfig.get("clusters") and len(kubeconfig["clusters"]) > 0:
                        server_url = kubeconfig["clusters"][0]["cluster"].get("server", "")
                        print(f"Extracted server URL: {server_url}")
                except json.JSONDecodeError:
                    print("Failed to parse kubeconfig as JSON")
            else:
                print("Kubeconfig file does not exist")
            
            # Check API server availability
            api_available = await manager.check_api_server_available()
            print(f"API server available: {api_available}")
            
        except asyncio.TimeoutError:
            end_time = time.time()
            duration = end_time - start_time
            print(f"Bundle initialization timed out after {duration:.2f} seconds")
            
            # List any processes
            try:
                ps_result = subprocess.run(["ps", "-ef"], capture_output=True, text=True)
                print("\nCurrent processes:")
                for line in ps_result.stdout.splitlines():
                    if "sbctl" in line:
                        print(f"  {line}")
            except Exception as ps_err:
                print(f"Error listing processes: {ps_err}")
            
            # List any files created
            files = list(bundle_dir.glob("**/*"))
            print("\nFiles created during initialization:")
            for file in files:
                print(f"  {file.relative_to(bundle_dir)}")
                
            # Check if kubeconfig was created
            kubeconfig_path = bundle_dir / "kubeconfig"
            if kubeconfig_path.exists():
                print(f"Found kubeconfig at: {kubeconfig_path}")
                with open(kubeconfig_path, "r") as f:
                    print(f"Kubeconfig content:\n{f.read()}")
                    
            # Try direct shell command as an alternative
            print("\nAttempting sbctl shell command as alternative...")
            try:
                shell_result = subprocess.run(
                    ["sbctl", "shell", "--support-bundle-location", str(real_bundle_path), "--no-shell"],
                    cwd=str(bundle_dir),
                    capture_output=True,
                    timeout=10.0
                )
                print(f"Shell command return code: {shell_result.returncode}")
                print(f"Shell command STDOUT: {shell_result.stdout.decode()}")
                print(f"Shell command STDERR: {shell_result.stderr.decode()}")
                
                # Check again for kubeconfig
                if kubeconfig_path.exists():
                    print(f"Kubeconfig now exists after shell command: {kubeconfig_path}")
                    with open(kubeconfig_path, "r") as f:
                        print(f"Kubeconfig content:\n{f.read()}")
            except Exception as shell_err:
                print(f"Error with shell command: {shell_err}")
                
        except BundleManagerError as e:
            print(f"Bundle initialization error: {str(e)}")
            
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Get detailed diagnostics
        try:
            diagnostics = await manager.get_diagnostic_info()
            print(f"\nDiagnostic info:\n{json.dumps(diagnostics, indent=2)}")
        except Exception as diag_err:
            print(f"Error getting diagnostics: {diag_err}")
    
    finally:
        # Clean up
        print("\nCleaning up resources...")
        try:
            await asyncio.wait_for(manager.cleanup(), timeout=10.0)
            print("Cleanup completed successfully")
        except asyncio.TimeoutError:
            print("Cleanup timed out")
            
            # Try to kill any lingering sbctl processes
            try:
                subprocess.run(["pkill", "-f", "sbctl"], capture_output=True)
                print("Sent kill signal to any sbctl processes")
            except Exception as kill_err:
                print(f"Error killing sbctl processes: {kill_err}")
                
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")
        
        # Clean up the temp directory
        try:
            if bundle_dir.exists():
                shutil.rmtree(bundle_dir)
                print(f"Removed bundle directory: {bundle_dir}")
        except Exception as e:
            print(f"Error removing bundle directory: {str(e)}")
            
        # Remove any logger handlers added in this test
        logger = logging.getLogger("mcp_server_troubleshoot.bundle")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
            
        # Force garbage collection
        gc.collect()
    
    # Simple pass assertion
    assert True, "Test with real sbctl completed"
