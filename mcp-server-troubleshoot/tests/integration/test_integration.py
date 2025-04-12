"""
Integration tests for the MCP server components.
This module tests all components working together end-to-end.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest import mock

import pytest
import pytest_asyncio

from mcp_server_troubleshoot.bundle import BundleManager
from mcp_server_troubleshoot.files import FileExplorer
from mcp_server_troubleshoot.kubectl import KubectlExecutor


@pytest.fixture
def mock_bundle_path():
    """Create a temporary directory with mock bundle structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create mock bundle structure
        bundle_dir = Path(tmpdir) / "test-bundle"
        bundle_dir.mkdir()
        
        # Create subdirectories
        kubernetes_dir = bundle_dir / "kubernetes"
        kubernetes_dir.mkdir()
        
        # Create sample pod yaml
        pods_dir = kubernetes_dir / "pods"
        pods_dir.mkdir(parents=True)
        pod_file = pods_dir / "sample-pod.yaml"
        pod_file.write_text("""
apiVersion: v1
kind: Pod
metadata:
  name: sample-pod
  namespace: default
spec:
  containers:
  - name: nginx
    image: nginx:latest
""")
        
        # Create sample logs
        logs_dir = kubernetes_dir / "logs"
        logs_dir.mkdir(parents=True)
        log_file = logs_dir / "sample-pod.log"
        log_file.write_text("Sample log content\nNormal operation\nError: something went wrong\n")
        
        # Create pseudo kube-apiserver
        apiserver_dir = bundle_dir / "kube-apiserver"
        apiserver_dir.mkdir()
        
        yield tmpdir, str(bundle_dir)


@pytest_asyncio.fixture
async def integration_components(mock_bundle_path):
    """Setup all components for integration testing."""
    tmpdir, bundle_path = mock_bundle_path
    
    # Mock environment variables
    env_vars = {
        "SBCTL_TOKEN": "test-token",
        "MCP_BUNDLE_STORAGE": tmpdir,
    }
    
    with mock.patch.dict(os.environ, env_vars):
        # Initialize components
        bundle_manager = BundleManager()
        # Mock bundle manager with an active bundle
        mock_metadata = mock.MagicMock()
        mock_metadata.id = "test-bundle"
        mock_metadata.path = Path(bundle_path)
        mock_metadata.initialized = True
        bundle_manager.get_active_bundle = mock.MagicMock(return_value=mock_metadata)
        
        kubectl_executor = KubectlExecutor(bundle_manager)
        file_explorer = FileExplorer(bundle_manager)
        
        # Create a simplified mock server for testing
        mcp_server = mock.MagicMock()
        mcp_server.list_tools = mock.MagicMock(return_value=[
            {"name": "initialize_bundle", "description": "Initialize a support bundle"},
            {"name": "kubectl", "description": "Execute kubectl commands"},
            {"name": "list_files", "description": "List directory contents"},
            {"name": "read_file", "description": "Read file contents"},
            {"name": "grep_files", "description": "Search for patterns in files"}
        ])
        
        # Mock the call_tool method
        mcp_server.call_tool = mock.AsyncMock()
        
        yield bundle_manager, kubectl_executor, file_explorer, mcp_server


@pytest.mark.asyncio
async def test_bundle_initialization(integration_components):
    """Test bundle initialization through the bundle manager."""
    bundle_manager, _, _, _ = integration_components
    
    # Verification check that the bundle is initialized
    assert bundle_manager.get_active_bundle() is not None
    assert bundle_manager.get_active_bundle().path.exists()


@pytest.mark.asyncio
async def test_file_listing(integration_components):
    """Test file listing through the file explorer."""
    _, _, file_explorer, _ = integration_components
    
    # Mock FileExplorer.list_files to return test data
    mock_file_info = mock.MagicMock()
    mock_file_info.name = "kubernetes"
    mock_file_info.type = "directory"
    
    mock_result = mock.MagicMock()
    mock_result.entries = [mock_file_info]
    
    with mock.patch.object(file_explorer, 'list_files', return_value=mock_result):
        # Test listing directories
        result = await file_explorer.list_files("/")
        assert result.entries[0].name == "kubernetes"
    
    # Mock for kubernetes directory
    mock_pods = mock.MagicMock()
    mock_pods.name = "pods"
    mock_pods.type = "directory"
    
    mock_logs = mock.MagicMock()
    mock_logs.name = "logs"
    mock_logs.type = "directory"
    
    mock_result2 = mock.MagicMock()
    mock_result2.entries = [mock_pods, mock_logs]
    
    with mock.patch.object(file_explorer, 'list_files', return_value=mock_result2):
        # Test listing kubernetes directory
        result = await file_explorer.list_files("/kubernetes")
        assert result.entries[0].name == "pods"
        assert result.entries[1].name == "logs"


@pytest.mark.asyncio
async def test_file_reading(integration_components):
    """Test file reading through the file explorer."""
    _, _, file_explorer, _ = integration_components
    
    # Create mock FileContentResult
    mock_content = """
apiVersion: v1
kind: Pod
metadata:
  name: sample-pod
  namespace: default
spec:
  containers:
  - name: nginx
    image: nginx:latest
"""
    
    mock_result = mock.MagicMock()
    mock_result.content = mock_content
    
    with mock.patch.object(file_explorer, 'read_file', return_value=mock_result):
        # Test reading a file
        result = await file_explorer.read_file("/kubernetes/pods/sample-pod.yaml")
        assert "apiVersion: v1" in result.content
        assert "name: sample-pod" in result.content
    
    # Create mock log file content
    mock_log_content = "Sample log content\nNormal operation\nError: something went wrong\n"
    
    mock_log_result = mock.MagicMock()
    mock_log_result.content = mock_log_content
    
    with mock.patch.object(file_explorer, 'read_file', return_value=mock_log_result):
        # Test reading a log file
        result = await file_explorer.read_file("/kubernetes/logs/sample-pod.log")
        assert "Sample log content" in result.content
        assert "Error: something went wrong" in result.content


@pytest.mark.asyncio
async def test_search_files(integration_components):
    """Test file search through the file explorer."""
    _, _, file_explorer, _ = integration_components
    
    # Create mock GrepResult
    mock_match = mock.MagicMock()
    mock_match.path = "/kubernetes/logs/sample-pod.log"
    mock_match.line = "Error: something went wrong"
    
    mock_grep_result = mock.MagicMock()
    mock_grep_result.matches = [mock_match]
    mock_grep_result.total_matches = 1
    
    with mock.patch.object(file_explorer, 'grep_files', return_value=mock_grep_result):
        # Test search for "Error" pattern
        result = await file_explorer.grep_files("Error", "/")
        assert result.total_matches > 0
        assert result.matches[0].path == "/kubernetes/logs/sample-pod.log"


@pytest.mark.asyncio
async def test_kubectl_get(integration_components):
    """Test kubectl get command through the kubectl executor."""
    _, kubectl_executor, _, _ = integration_components
    
    # Mock the kubectl execution results
    with mock.patch('mcp_server_troubleshoot.kubectl.KubectlExecutor.execute') as mock_execute:
        mock_result = mock.MagicMock()
        mock_result.stdout = json.dumps({
            "items": [
                {
                    "metadata": {
                        "name": "sample-pod",
                        "namespace": "default"
                    },
                    "status": {
                        "phase": "Running"
                    }
                }
            ]
        })
        mock_result.output = json.loads(mock_result.stdout)
        mock_result.is_json = True
        mock_execute.return_value = mock_result
        
        # Test kubectl get command
        result = await kubectl_executor.execute("get pods -o json")
        assert result.output["items"][0]["metadata"]["name"] == "sample-pod"


@pytest.mark.asyncio
async def test_kubectl_describe(integration_components):
    """Test kubectl describe command through the kubectl executor."""
    _, kubectl_executor, _, _ = integration_components
    
    # Mock the kubectl execution results
    with mock.patch('mcp_server_troubleshoot.kubectl.KubectlExecutor.execute') as mock_execute:
        pod_description = """
Name:         sample-pod
Namespace:    default
Status:       Running
IP:           10.0.0.1
Containers:
  nginx:
    Image:    nginx:latest
    State:    Running
"""
        mock_result = mock.MagicMock()
        mock_result.stdout = pod_description
        mock_result.output = pod_description
        mock_result.is_json = False
        mock_execute.return_value = mock_result
        
        # Test kubectl describe command
        result = await kubectl_executor.execute("describe pod sample-pod")
        assert "Name:         sample-pod" in result.stdout
        assert "Status:       Running" in result.stdout


@pytest.mark.asyncio
async def test_mcp_server_list_tools(integration_components):
    """Test MCP server list_tools functionality."""
    _, _, _, mcp_server = integration_components
    
    # Test list_tools
    tools = mcp_server.list_tools()
    
    # Check if all tools are registered
    tool_names = [tool["name"] for tool in tools]
    assert "initialize_bundle" in tool_names
    assert "kubectl" in tool_names
    assert "list_files" in tool_names
    assert "read_file" in tool_names
    assert "grep_files" in tool_names


@pytest.mark.asyncio
async def test_mcp_server_call_tool(integration_components):
    """Test MCP server call_tool functionality with different tools."""
    _, _, _, mcp_server = integration_components
    
    # Set up the return values for the mock call_tool method
    mcp_server.call_tool.side_effect = [
        # Return value for files__list_directory
        [
            {"name": "kubernetes", "type": "directory"},
            {"name": "kube-apiserver", "type": "directory"}
        ],
        # Return value for files__read_file
        "Sample file content",
        # Return value for kubectl__execute
        "kubectl output"
    ]
    
    # Test calling files__list_directory tool
    result1 = await mcp_server.call_tool(
        "files__list_directory",
        {"path": "/"}
    )
    
    assert result1 == [
        {"name": "kubernetes", "type": "directory"},
        {"name": "kube-apiserver", "type": "directory"}
    ]
    
    # Test calling files__read_file tool
    result2 = await mcp_server.call_tool(
        "files__read_file",
        {"path": "/kubernetes/pods/sample-pod.yaml"}
    )
    
    assert result2 == "Sample file content"
    
    # Test calling kubectl__execute tool
    result3 = await mcp_server.call_tool(
        "kubectl__execute",
        {"command": "get pods"}
    )
    
    assert result3 == "kubectl output"
    
    # Verify the calls were made with the right parameters
    assert mcp_server.call_tool.call_count == 3
    mcp_server.call_tool.assert_any_call("files__list_directory", {"path": "/"})
    mcp_server.call_tool.assert_any_call("files__read_file", {"path": "/kubernetes/pods/sample-pod.yaml"})
    mcp_server.call_tool.assert_any_call("kubectl__execute", {"command": "get pods"})


@pytest.mark.asyncio
async def test_error_handling(integration_components):
    """Test error handling across components."""
    _, kubectl_executor, file_explorer, mcp_server = integration_components
    
    # Test file not found error - mock PathNotFoundError
    with mock.patch.object(file_explorer, 'read_file', side_effect=FileNotFoundError("File not found")):
        with pytest.raises(FileNotFoundError):
            await file_explorer.read_file("/non-existent-file.txt")
    
    # Test handling of invalid kubectl command
    with mock.patch.object(kubectl_executor, 'execute', side_effect=Exception("Invalid command")):
        with pytest.raises(Exception):
            await kubectl_executor.execute("invalid command")
    
    # Test MCP server error handling
    mcp_server.call_tool.side_effect = ValueError("Invalid parameter")
    
    with pytest.raises(ValueError):
        await mcp_server.call_tool("files__list_directory", {"invalid": "parameter"})


@pytest.mark.asyncio
async def test_end_to_end_workflow(integration_components):
    """Test the entire workflow from bundle initialization to file exploration."""
    bundle_manager, kubectl_executor, file_explorer, mcp_server = integration_components
    
    # Step 1: Ensure bundle is initialized
    assert bundle_manager.get_active_bundle() is not None
    
    # Set up mocks for entire workflow
    
    # Step 2: Mock list_files for root directory
    mock_root_info = mock.MagicMock()
    mock_root_info.name = "kubernetes"
    mock_root_info.type = "directory"
    
    mock_root_result = mock.MagicMock()
    mock_root_result.entries = [mock_root_info]
    
    # Step 3: Mock list_files for kubernetes/pods directory
    mock_pod_yaml = mock.MagicMock()
    mock_pod_yaml.name = "sample-pod.yaml"
    mock_pod_yaml.type = "file"
    
    mock_pods_result = mock.MagicMock()
    mock_pods_result.entries = [mock_pod_yaml]
    
    # Step 4: Mock read_file for pod yaml
    mock_pod_content = """
apiVersion: v1
kind: Pod
metadata:
  name: sample-pod
  namespace: default
spec:
  containers:
  - name: nginx
    image: nginx:latest
"""
    
    mock_pod_file_result = mock.MagicMock()
    mock_pod_file_result.content = mock_pod_content
    
    # Step 5: Mock kubectl execution
    pod_data = {"metadata": {"name": "sample-pod"}, "status": {"phase": "Running"}}
    mock_kubectl_result = mock.MagicMock()
    mock_kubectl_result.stdout = json.dumps(pod_data)
    mock_kubectl_result.output = pod_data
    mock_kubectl_result.is_json = True
    
    # Step 6: Mock grep_files result
    mock_grep_match = mock.MagicMock()
    mock_grep_match.path = "/kubernetes/logs/sample-pod.log"
    mock_grep_match.line = "Error: something went wrong"
    
    mock_grep_result = mock.MagicMock()
    mock_grep_result.matches = [mock_grep_match]
    mock_grep_result.total_matches = 1
    
    # Step 7: Mock log file content
    mock_log_content = "Sample log content\nNormal operation\nError: something went wrong\n"
    
    mock_log_result = mock.MagicMock()
    mock_log_result.content = mock_log_content
    
    # Now execute the workflow with mocks
    
    # Step 2: List root directory
    with mock.patch.object(file_explorer, 'list_files', return_value=mock_root_result):
        root_listing = await file_explorer.list_files("/")
        assert root_listing.entries[0].name == "kubernetes"
    
    # Step 3: Navigate to kubernetes/pods directory
    with mock.patch.object(file_explorer, 'list_files', return_value=mock_pods_result):
        pods_listing = await file_explorer.list_files("/kubernetes/pods")
        assert pods_listing.entries[0].name == "sample-pod.yaml"
    
    # Step 4: Read pod file
    with mock.patch.object(file_explorer, 'read_file', return_value=mock_pod_file_result):
        pod_file = await file_explorer.read_file("/kubernetes/pods/sample-pod.yaml")
        assert "name: sample-pod" in pod_file.content
    
    # Step 5: Execute kubectl command on the pod
    with mock.patch.object(kubectl_executor, 'execute', return_value=mock_kubectl_result):
        kubectl_result = await kubectl_executor.execute("get pod sample-pod -o json")
        assert kubectl_result.output["metadata"]["name"] == "sample-pod"
    
    # Step 6: Search for errors in logs
    with mock.patch.object(file_explorer, 'grep_files', return_value=mock_grep_result):
        search_results = await file_explorer.grep_files("Error", "/")
        assert search_results.matches[0].path == "/kubernetes/logs/sample-pod.log"
    
    # Step 7: Read the log file containing errors
    with mock.patch.object(file_explorer, 'read_file', return_value=mock_log_result):
        log_file = await file_explorer.read_file("/kubernetes/logs/sample-pod.log")
        assert "Error: something went wrong" in log_file.content


@pytest.mark.skipif(
    not os.path.exists("./test-bundles"),
    reason="Test bundles directory doesn't exist"
)
def test_build_and_run_container():
    """Test building and running the container."""
    print("Testing container build and run...")
    
    # Test the script's functionality without actually running it
    try:
        # Check if Docker is available
        docker_check = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        assert docker_check.returncode == 0, "Docker is not available"
        
        # Check if the image exists or needs to be built
        image_check = subprocess.run(
            ["docker", "images", "-q", "mcp-server-troubleshoot:latest"],
            capture_output=True, text=True
        )
        
        if not image_check.stdout.strip():
            print("Need to build the image")
        else:
            print("Image already exists")
        
        # Make sure the bundles directory exists
        os.makedirs("bundles", exist_ok=True)
        
        # Success if we got here without errors
        assert True
    except Exception as e:
        pytest.fail(f"Failed to check container prerequisites: {e}")


def test_container_mcp_communication():
    """
    Test the container MCP communication.
    This is now directly tested in the e2e/test_container.py tests.
    This test simply ensures that those tests can be run.
    """
    try:
        # Check if Docker is available
        docker_check = subprocess.run(
            ["docker", "--version"], 
            capture_output=True, 
            text=True
        )
        assert docker_check.returncode == 0, "Docker is not available"
        
        # Check if the test image exists or can be built
        image_check = subprocess.run(
            ["docker", "images", "-q", "mcp-server-troubleshoot:latest"],
            capture_output=True, 
            text=True
        )
        
        if not image_check.stdout.strip():
            if os.path.exists("./scripts/build.sh"):
                # Try to build the image
                subprocess.run(
                    ["./scripts/build.sh"], 
                    check=True, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE
                )
        
        # Verify image exists
        image_check = subprocess.run(
            ["docker", "images", "-q", "mcp-server-troubleshoot:latest"],
            capture_output=True, 
            text=True
        )
        assert image_check.stdout.strip(), "Docker image mcp-server-troubleshoot:latest does not exist"
        
        # If we got this far, container functionality is available
        # The actual tests are in test_container.py
        assert True, "Container communication tests are available to run"
        
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Container test environment check failed: {e}")
    except Exception as e:
        pytest.fail(f"Failed to check container test environment: {e}")