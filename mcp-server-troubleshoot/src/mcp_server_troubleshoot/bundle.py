"""
Bundle Manager for Kubernetes support bundles.

This module implements the Bundle Manager component, which is responsible for
handling the lifecycle of Kubernetes support bundles, including downloading,
extraction, initialization, and cleanup.
"""

import asyncio
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

import aiohttp
from pydantic import BaseModel, Field, field_validator

# Set up logging
logger = logging.getLogger(__name__)

# Constants for resource limits - can be overridden by environment variables
DEFAULT_DOWNLOAD_SIZE = 1024 * 1024 * 1024  # 1 GB
DEFAULT_DOWNLOAD_TIMEOUT = 300  # 5 minutes
DEFAULT_INITIALIZATION_TIMEOUT = 120  # 2 minutes

# Override with environment variables if provided
MAX_DOWNLOAD_SIZE = int(os.environ.get("MAX_DOWNLOAD_SIZE", DEFAULT_DOWNLOAD_SIZE))
MAX_DOWNLOAD_TIMEOUT = int(os.environ.get("MAX_DOWNLOAD_TIMEOUT", DEFAULT_DOWNLOAD_TIMEOUT))
MAX_INITIALIZATION_TIMEOUT = int(os.environ.get("MAX_INITIALIZATION_TIMEOUT", DEFAULT_INITIALIZATION_TIMEOUT))

logger.debug(f"Using MAX_DOWNLOAD_SIZE: {MAX_DOWNLOAD_SIZE / 1024 / 1024:.1f} MB")
logger.debug(f"Using MAX_DOWNLOAD_TIMEOUT: {MAX_DOWNLOAD_TIMEOUT} seconds")
logger.debug(f"Using MAX_INITIALIZATION_TIMEOUT: {MAX_INITIALIZATION_TIMEOUT} seconds")


class BundleMetadata(BaseModel):
    """
    Metadata for an initialized support bundle.
    """

    id: str = Field(description="The unique identifier for the bundle")
    source: str = Field(description="The source of the bundle (URL or local path)")
    path: Path = Field(description="The path to the extracted bundle")
    kubeconfig_path: Path = Field(description="The path to the kubeconfig file")
    initialized: bool = Field(description="Whether the bundle has been initialized with sbctl")


class InitializeBundleArgs(BaseModel):
    """
    Arguments for initializing a support bundle.
    """

    source: str = Field(description="The source of the bundle (URL or local path)")
    force: bool = Field(
        False, description="Whether to force re-initialization if a bundle is already active"
    )

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        """
        Validate the bundle source.

        Args:
            v: The source string to validate

        Returns:
            The validated source string

        Raises:
            ValueError: If the source is invalid
        """
        # Check if it's a URL
        try:
            result = urlparse(v)
            if all([result.scheme, result.netloc]):
                return v
        except Exception:
            pass

        # Check if it's a local file
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Bundle source not found: {v}")

        if not path.is_file():
            raise ValueError(f"Bundle source must be a file: {v}")

        return v


class BundleManagerError(Exception):
    """Base exception for bundle manager errors."""

    pass


class BundleDownloadError(BundleManagerError):
    """Exception raised when a bundle could not be downloaded."""

    pass


class BundleInitializationError(BundleManagerError):
    """Exception raised when a bundle could not be initialized."""

    pass


class BundleNotFoundError(BundleManagerError):
    """Exception raised when a requested bundle is not found."""

    pass


class BundleManager:
    """
    Manages the lifecycle of Kubernetes support bundles.

    This class handles downloading, extraction, initialization, and cleanup of
    support bundles. It uses sbctl to create a Kubernetes API server emulation
    from the bundle.
    """

    def __init__(self, bundle_dir: Optional[Path] = None) -> None:
        """
        Initialize the Bundle Manager.

        Args:
            bundle_dir: The directory where bundles will be stored. If not provided,
                a temporary directory will be used.
        """
        self.bundle_dir = bundle_dir or Path(tempfile.mkdtemp(prefix="k8s-bundle-"))
        self.bundle_dir.mkdir(parents=True, exist_ok=True)
        self.active_bundle: Optional[BundleMetadata] = None
        self.sbctl_process: Optional[asyncio.subprocess.Process] = None

    async def initialize_bundle(self, source: str, force: bool = False) -> BundleMetadata:
        """
        Initialize a support bundle from a source.

        Args:
            source: The source of the bundle (URL or local path)
            force: Whether to force re-initialization if a bundle is already active

        Returns:
            Metadata for the initialized bundle

        Raises:
            BundleManagerError: If the bundle could not be initialized
        """
        if self.active_bundle and not force:
            logger.info(f"Using already initialized bundle: {self.active_bundle.id}")
            return self.active_bundle

        await self._cleanup_active_bundle()

        logger.info(f"Initializing bundle from source: {source}")
        try:
            # Determine if the source is a URL or local file
            if source.startswith(("http://", "https://")):
                bundle_path = await self._download_bundle(source)
            else:
                bundle_path = Path(source)
                if not bundle_path.exists():
                    raise BundleNotFoundError(f"Bundle not found: {source}")

            # Generate a unique ID for the bundle
            bundle_id = self._generate_bundle_id(source)

            # Create a directory for the bundle
            bundle_output_dir = self.bundle_dir / bundle_id
            bundle_output_dir.mkdir(parents=True, exist_ok=True)

            # Initialize the bundle with sbctl
            kubeconfig_path = await self._initialize_with_sbctl(bundle_path, bundle_output_dir)

            # Create and store bundle metadata
            metadata = BundleMetadata(
                id=bundle_id,
                source=source,
                path=bundle_output_dir,
                kubeconfig_path=kubeconfig_path,
                initialized=True,
            )
            self.active_bundle = metadata

            logger.info(f"Bundle initialized: {bundle_id}")
            return metadata

        except (BundleDownloadError, BundleInitializationError) as e:
            logger.error(f"Failed to initialize bundle: {str(e)}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error initializing bundle: {str(e)}")
            raise BundleManagerError(f"Failed to initialize bundle: {str(e)}")

    async def _download_bundle(self, url: str) -> Path:
        """
        Download a support bundle from a URL.

        Args:
            url: The URL to download the bundle from

        Returns:
            The path to the downloaded bundle

        Raises:
            BundleDownloadError: If the bundle could not be downloaded
        """
        logger.info(f"Downloading bundle from: {url}")

        parsed_url = urlparse(url)
        filename = (
            os.path.basename(parsed_url.path) or f"bundle_{self._generate_bundle_id(url)}.tar.gz"
        )
        download_path = self.bundle_dir / filename

        try:
            headers = {}
            # Add authentication if provided via environment variables
            token = os.environ.get("SBCTL_TOKEN")
            if token:
                headers["Authorization"] = f"Bearer {token}"

            # Set a timeout for the download to prevent hanging
            timeout = aiohttp.ClientTimeout(total=MAX_DOWNLOAD_TIMEOUT)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        raise BundleDownloadError(
                            f"Failed to download bundle from {url}: HTTP {response.status}"
                        )

                    # Check content length if available
                    content_length = response.content_length
                    if content_length and content_length > MAX_DOWNLOAD_SIZE:
                        raise BundleDownloadError(
                            f"Bundle size ({content_length / 1024 / 1024:.1f} MB) exceeds maximum allowed size "
                            f"({MAX_DOWNLOAD_SIZE / 1024 / 1024:.1f} MB)"
                        )

                    # Track total downloaded size
                    total_size = 0
                    with download_path.open("wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            total_size += len(chunk)

                            # Check size limit during download
                            if total_size > MAX_DOWNLOAD_SIZE:
                                # Close and remove the partial file
                                f.close()
                                download_path.unlink()
                                raise BundleDownloadError(
                                    f"Bundle download exceeded maximum allowed size "
                                    f"({MAX_DOWNLOAD_SIZE / 1024 / 1024:.1f} MB)"
                                )

                            f.write(chunk)

                    logger.info(f"Downloaded {total_size / 1024 / 1024:.1f} MB from {url}")

            logger.info(f"Bundle downloaded to: {download_path}")
            return download_path
        except Exception as e:
            logger.exception(f"Error downloading bundle from {url}: {str(e)}")
            if download_path.exists():
                download_path.unlink()
            raise BundleDownloadError(f"Failed to download bundle from {url}: {str(e)}")

    async def _initialize_with_sbctl(self, bundle_path: Path, output_dir: Path) -> Path:
        """
        Initialize a support bundle with sbctl.

        Args:
            bundle_path: The path to the bundle file
            output_dir: The directory where the bundle will be extracted

        Returns:
            The path to the kubeconfig file

        Raises:
            BundleInitializationError: If the bundle could not be initialized
        """
        logger.info(f"Initializing bundle with sbctl: {bundle_path}")

        # sbctl creates the kubeconfig in the current directory with a fixed name
        # Change our working directory to the output directory and look for 'kubeconfig' there
        os.chdir(output_dir)
        kubeconfig_path = output_dir / "kubeconfig"

        try:
            # Kill any existing sbctl process
            await self._terminate_sbctl_process()

            # Start sbctl in serve mode with the bundle
            # Since sbctl may create files in the current directory, we'll start it from our output directory
            os.chdir(output_dir)

            # Use the serve command to start the API server
            cmd = [
                "sbctl",
                "serve",
                "--support-bundle-location",
                str(bundle_path),
            ]

            # sbctl will write a kubeconfig file in the current working directory
            # The default name is 'kubeconfig'

            logger.debug(f"Running command: {' '.join(cmd)}")

            # Start the process
            self.sbctl_process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            # Wait for initialization to complete
            await self._wait_for_initialization(kubeconfig_path)

            if not kubeconfig_path.exists():
                raise BundleInitializationError(
                    f"Failed to initialize bundle: kubeconfig not created at {kubeconfig_path}"
                )

            logger.info(f"Bundle initialized with kubeconfig at: {kubeconfig_path}")
            return kubeconfig_path

        except Exception as e:
            error_message = str(e)
            stderr_output = ""

            # Try to capture any stderr output from the process for better diagnostics
            if self.sbctl_process and self.sbctl_process.stderr:
                try:
                    stderr_data = await asyncio.wait_for(
                        self.sbctl_process.stderr.read(4096), timeout=1.0
                    )
                    if stderr_data:
                        stderr_output = stderr_data.decode("utf-8", errors="replace")
                        logger.error(f"sbctl stderr output: {stderr_output}")
                except Exception as stderr_err:
                    logger.debug(f"Could not read stderr: {stderr_err}")

            # Add stderr to the error message if available
            if stderr_output:
                error_message = f"{error_message} - Process stderr: {stderr_output}"

            logger.exception(f"Error initializing bundle with sbctl: {error_message}")

            # Terminate the process
            await self._terminate_sbctl_process()

            raise BundleInitializationError(
                f"Failed to initialize bundle with sbctl: {error_message}"
            )

    async def _wait_for_initialization(
        self, kubeconfig_path: Path, timeout: float = MAX_INITIALIZATION_TIMEOUT
    ) -> None:
        """
        Wait for sbctl initialization to complete.

        Args:
            kubeconfig_path: The path to the kubeconfig file
            timeout: The maximum time to wait for initialization

        Raises:
            BundleInitializationError: If initialization times out
        """
        start_time = asyncio.get_event_loop().time()
        error_message = ""

        # Attempt to read process output for diagnostic purposes
        if self.sbctl_process and self.sbctl_process.stdout and self.sbctl_process.stderr:
            stdout_data = ""
            stderr_data = ""

            try:
                # Try to read without blocking the entire process
                stdout_data = await asyncio.wait_for(
                    self.sbctl_process.stdout.read(1024), timeout=1.0
                )
                stderr_data = await asyncio.wait_for(
                    self.sbctl_process.stderr.read(1024), timeout=1.0
                )

                if stdout_data:
                    logger.debug(f"sbctl stdout: {stdout_data.decode('utf-8', errors='replace')}")
                if stderr_data:
                    logger.debug(f"sbctl stderr: {stderr_data.decode('utf-8', errors='replace')}")
                    error_message = stderr_data.decode("utf-8", errors="replace")
            except (asyncio.TimeoutError, Exception) as e:
                logger.debug(f"Error reading process output: {str(e)}")

        # Wait for the kubeconfig file to appear
        while asyncio.get_event_loop().time() - start_time < timeout:
            if kubeconfig_path.exists():
                logger.info(f"Kubeconfig found at: {kubeconfig_path}")
                
                # Wait an additional second for the API server to start listening
                await asyncio.sleep(1.0)
                
                # Check if the API server is actually responding
                if await self.check_api_server_available():
                    logger.info("API server is available and responding")
                    return
                else:
                    logger.warning("Kubeconfig found but API server is not responding yet")
            
            # Check if the process is still running
            if self.sbctl_process and self.sbctl_process.returncode is not None:
                # Process exited before kubeconfig was created
                error_message = f"sbctl process exited with code {self.sbctl_process.returncode} before initialization completed"
                break

            # Look for any files created in the directory to debug
            dir_contents = list(kubeconfig_path.parent.glob("*"))
            if dir_contents:
                logger.debug(
                    f"Files in {kubeconfig_path.parent}: {[file.name for file in dir_contents]}"
                )

            await asyncio.sleep(0.5)

        # If we got here, the timeout occurred
        error_details = f" Error details: {error_message}" if error_message else ""
        raise BundleInitializationError(
            f"Timeout waiting for bundle initialization after {timeout} seconds.{error_details}"
        )

    async def _terminate_sbctl_process(self) -> None:
        """
        Terminate the sbctl process if it's running.

        This helper method centralizes process termination logic to avoid duplication.
        """
        if self.sbctl_process:
            try:
                logger.debug("Terminating sbctl process...")
                self.sbctl_process.terminate()
                try:
                    await asyncio.wait_for(self.sbctl_process.wait(), timeout=3.0)
                    logger.debug("sbctl process terminated gracefully")
                except (asyncio.TimeoutError, ProcessLookupError) as e:
                    logger.warning(f"Failed to terminate sbctl process gracefully: {str(e)}")
                    if self.sbctl_process:
                        try:
                            logger.debug("Killing sbctl process...")
                            self.sbctl_process.kill()
                            logger.debug("sbctl process killed")
                        except ProcessLookupError:
                            logger.debug("Process already gone when trying to kill")
            except Exception as e:
                logger.warning(f"Error during process termination: {str(e)}")
                
            # Always set to None regardless of success
            self.sbctl_process = None
            
            # Check for any lingering mock_sbctl.pid file in the output directory
            # This helps us clean up in case the signal handling didn't work
            if self.active_bundle and self.active_bundle.path.exists():
                pid_file = self.active_bundle.path / "mock_sbctl.pid"
                if pid_file.exists():
                    try:
                        with open(pid_file, "r") as f:
                            pid = int(f.read().strip())
                        
                        # Try to kill the process if it exists
                        try:
                            logger.debug(f"Killing leftover process with PID {pid}")
                            os.kill(pid, signal.SIGTERM)
                            # Wait briefly for termination
                            await asyncio.sleep(0.5)
                            try:
                                # Check if process is gone
                                os.kill(pid, 0)
                                # If we get here, process still exists, try SIGKILL
                                logger.debug(f"Process {pid} still exists, sending SIGKILL")
                                os.kill(pid, signal.SIGKILL)
                            except ProcessLookupError:
                                logger.debug(f"Process {pid} terminated successfully")
                        except ProcessLookupError:
                            logger.debug(f"Process {pid} not found")
                        except PermissionError:
                            logger.warning(f"Permission error trying to kill process {pid}")
                            
                        # Remove the PID file
                        try:
                            pid_file.unlink()
                            logger.debug(f"Removed PID file: {pid_file}")
                        except Exception as e:
                            logger.warning(f"Failed to remove PID file: {e}")
                    except Exception as e:
                        logger.warning(f"Error handling leftover PID file: {e}")

    async def _cleanup_active_bundle(self) -> None:
        """
        Clean up the active bundle.
        """
        if self.active_bundle:
            logger.info(f"Cleaning up active bundle: {self.active_bundle.id}")

            # Stop the sbctl process if it's running
            await self._terminate_sbctl_process()

            # Reset the active bundle
            self.active_bundle = None

    def _generate_bundle_id(self, source: str) -> str:
        """
        Generate a unique ID for a bundle.

        Args:
            source: The source of the bundle (URL or local path)

        Returns:
            A unique ID for the bundle
        """
        # Extract just the filename component from the path/URL
        filename = os.path.basename(source.rstrip("/"))

        # If empty (e.g., from a URL without a path component), use a default
        if not filename:
            filename = "bundle"

        # Strictly sanitize by only allowing alphanumeric chars, underscore, and hyphen
        # Replace any other characters with underscore
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", filename)

        # Ensure the ID starts with a letter or underscore (not a number or hyphen)
        # This prevents issues with some file systems and tools
        if sanitized and sanitized[0].isdigit() or sanitized and sanitized[0] == "-":
            sanitized = f"b_{sanitized}"

        # If sanitization resulted in an empty string, use a default name
        if not sanitized:
            sanitized = "bundle"

        # Add randomness to ensure uniqueness
        random_suffix = os.urandom(8).hex()  # Increased from 4 to 8 bytes for more entropy

        return f"{sanitized}_{random_suffix}"

    def is_initialized(self) -> bool:
        """
        Check if a bundle is currently initialized.

        Returns:
            True if a bundle is initialized, False otherwise
        """
        return self.active_bundle is not None and self.active_bundle.initialized

    def get_active_bundle(self) -> Optional[BundleMetadata]:
        """
        Get the currently active bundle.

        Returns:
            The active bundle metadata, or None if no bundle is active
        """
        return self.active_bundle
    
    async def check_api_server_available(self) -> bool:
        """
        Check if the Kubernetes API server is available.
        
        Returns:
            True if the API server is responding, False otherwise
        """
        # First check if sbctl process is running
        if not self.sbctl_process or self.sbctl_process.returncode is not None:
            logger.warning("sbctl process is not running")
            return False
        
        # Check if we have a kubeconfig to extract the port from
        port = 8080
        if self.active_bundle and self.active_bundle.kubeconfig_path.exists():
            try:
                with open(self.active_bundle.kubeconfig_path, "r") as f:
                    config = json.load(f)
                if config.get("clusters") and len(config["clusters"]) > 0:
                    server_url = config["clusters"][0]["cluster"].get("server", "")
                    if ":" in server_url:
                        # Extract port from URL like http://localhost:8091
                        port = int(server_url.split(":")[-1])
                        logger.debug(f"Extracted API server port from kubeconfig: {port}")
            except (json.JSONDecodeError, KeyError, ValueError, IndexError) as e:
                logger.warning(f"Failed to parse kubeconfig: {e}")
            
        # Also check the environment variable used by our mock for testing
        env_port = os.environ.get("MOCK_K8S_API_PORT")
        if env_port:
            try:
                port = int(env_port)
                logger.debug(f"Using API server port from environment: {port}")
            except ValueError:
                pass
            
        # Try to connect to the API server using aiohttp
        try:
            url = f"http://localhost:{port}/api"
            logger.debug(f"Checking API server at {url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=2.0) as response:
                    if response.status == 200:
                        logger.debug(f"API server is available at {url}")
                        return True
                    else:
                        logger.warning(f"API server returned status {response.status}")
                        return False
        except aiohttp.ClientError as e:
            logger.warning(f"Failed to connect to API server: {str(e)}")
            return False
    
    async def get_diagnostic_info(self) -> dict:
        """
        Get diagnostic information about the current bundle and sbctl.
        
        Returns:
            A dictionary with diagnostic information
        """
        diagnostics = {
            "sbctl_available": await self._check_sbctl_available(),
            "sbctl_process_running": self.sbctl_process is not None and self.sbctl_process.returncode is None,
            "api_server_available": await self.check_api_server_available(),
            "bundle_initialized": self.active_bundle is not None and self.active_bundle.initialized,
            "system_info": await self._get_system_info(),
        }
        
        # Add active bundle info if available
        if self.active_bundle:
            diagnostics["active_bundle"] = {
                "id": self.active_bundle.id,
                "source": self.active_bundle.source,
                "path": str(self.active_bundle.path),
                "kubeconfig_exists": self.active_bundle.kubeconfig_path.exists(),
                "kubeconfig_path": str(self.active_bundle.kubeconfig_path),
            }
            
        # Add sbctl process info if available
        if self.sbctl_process:
            diagnostics["sbctl_process"] = {
                "pid": self.sbctl_process.pid,
                "returncode": self.sbctl_process.returncode,
            }
            
        return diagnostics
    
    async def _check_sbctl_available(self) -> bool:
        """
        Check if sbctl is available in the current environment.
        
        Returns:
            True if sbctl is available, False otherwise
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                "which", "sbctl",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0 and stdout:
                logger.debug(f"sbctl found at: {stdout.decode().strip()}")
                return True
            else:
                logger.warning("sbctl not found")
                return False
        except Exception as e:
            logger.warning(f"Error checking sbctl availability: {str(e)}")
            return False
    
    async def _get_system_info(self) -> dict:
        """
        Get system information.
        
        Returns:
            A dictionary with system information
        """
        info = {}
        
        # Get the API port from environment or default
        ports_to_check = [8080]  # Default port
        
        # Check for port in environment variable
        env_port = os.environ.get("MOCK_K8S_API_PORT")
        if env_port:
            try:
                ports_to_check.insert(0, int(env_port))  # Check this port first
            except ValueError:
                pass
        
        # If we have an active bundle with a kubeconfig, extract the port
        if self.active_bundle and self.active_bundle.kubeconfig_path.exists():
            try:
                with open(self.active_bundle.kubeconfig_path, "r") as f:
                    config = json.load(f)
                if config.get("clusters") and len(config["clusters"]) > 0:
                    server_url = config["clusters"][0]["cluster"].get("server", "")
                    if ":" in server_url:
                        port = int(server_url.split(":")[-1])
                        if port not in ports_to_check:
                            ports_to_check.insert(0, port)
            except Exception:
                pass
        
        # Check all possible ports
        for port in ports_to_check:
            info[f"port_{port}_checked"] = True
            
            # Check network connections on the port
            try:
                proc = await asyncio.create_subprocess_exec(
                    "netstat", "-tuln",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                
                if proc.returncode == 0:
                    netstat_output = stdout.decode()
                    for line in netstat_output.splitlines():
                        if f":{port}" in line:
                            info[f"port_{port}_listening"] = True
                            info[f"port_{port}_details"] = line.strip()
                            break
                    else:
                        info[f"port_{port}_listening"] = False
                else:
                    info["netstat_error"] = stderr.decode()
            except Exception as e:
                info["netstat_error"] = str(e)
                
            # Try curl to test API server on this port
            try:
                url = f"http://localhost:{port}/api"
                proc = await asyncio.create_subprocess_exec(
                    "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                
                if proc.returncode == 0:
                    info[f"curl_{port}_status_code"] = stdout.decode().strip()
                else:
                    info[f"curl_{port}_error"] = stderr.decode()
            except Exception as e:
                info[f"curl_{port}_error"] = str(e)
        
        # Add environment info
        info["env_mock_k8s_api_port"] = os.environ.get("MOCK_K8S_API_PORT", "not set")
        
        return info

    async def cleanup(self) -> None:
        """
        Clean up all resources.

        This should be called when shutting down the server.
        """
        await self._cleanup_active_bundle()

        # Remove temporary directory if it was created by us
        if self.bundle_dir and str(self.bundle_dir).startswith(tempfile.gettempdir()):
            try:
                shutil.rmtree(self.bundle_dir)
                logger.info(f"Removed temporary bundle directory: {self.bundle_dir}")
            except Exception as e:
                logger.error(f"Failed to remove temporary bundle directory: {str(e)}")
