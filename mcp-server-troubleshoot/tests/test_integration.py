"""Integration tests for the MCP server components."""

import asyncio
import contextlib
import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from mcp_server_troubleshoot.bundle import BundleManager
from mcp_server_troubleshoot.files import FileExplorer
from mcp_server_troubleshoot.kubectl import KubectlExecutor
from mcp_server_troubleshoot.server import MCPServer


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


@pytest.fixture
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
        # Mock bundle init to use the created mock bundle
        bundle_manager.initialized_bundle = bundle_path
        
        kubectl_executor = KubectlExecutor(bundle_manager)
        file_explorer = FileExplorer(bundle_manager)
        
        mcp_server = MCPServer()
        
        # Register components with the server
        mcp_server.register_bundle_tools(bundle_manager)
        mcp_server.register_kubectl_tools(kubectl_executor)
        mcp_server.register_file_tools(file_explorer)
        
        yield bundle_manager, kubectl_executor, file_explorer, mcp_server


async def test_bundle_initialization(integration_components):
    """Test bundle initialization through the bundle manager."""
    bundle_manager, _, _, _ = integration_components
    
    # Verification check that the bundle is initialized
    assert bundle_manager.initialized_bundle is not None
    assert Path(bundle_manager.initialized_bundle).exists()


async def test_file_listing(integration_components):
    """Test file listing through the file explorer."""
    _, _, file_explorer, _ = integration_components
    
    # Test listing directories
    result = await file_explorer.list_directory("/")
    assert "kubernetes" in [item["name"] for item in result]
    
    # Test listing kubernetes directory
    result = await file_explorer.list_directory("/kubernetes")
    assert "pods" in [item["name"] for item in result]
    assert "logs" in [item["name"] for item in result]


async def test_file_reading(integration_components):
    """Test file reading through the file explorer."""
    _, _, file_explorer, _ = integration_components
    
    # Test reading a file
    result = await file_explorer.read_file("/kubernetes/pods/sample-pod.yaml")
    assert "apiVersion: v1" in result
    assert "name: sample-pod" in result
    
    # Test reading a log file
    result = await file_explorer.read_file("/kubernetes/logs/sample-pod.log")
    assert "Sample log content" in result
    assert "Error: something went wrong" in result


async def test_search_files(integration_components):
    """Test file search through the file explorer."""
    _, _, file_explorer, _ = integration_components
    
    # Test search for "Error" pattern
    result = await file_explorer.search_files("Error")
    assert len(result) > 0
    assert any("/kubernetes/logs/sample-pod.log" in match for match in result)


async def test_kubectl_get(integration_components):
    """Test kubectl get command through the kubectl executor."""
    _, kubectl_executor, _, _ = integration_components
    
    # Mock the kubectl execution results
    with mock.patch('mcp_server_troubleshoot.kubectl.KubectlExecutor._execute_kubectl') as mock_execute:
        mock_execute.return_value = json.dumps({
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
        
        # Test kubectl get command
        result = await kubectl_executor.execute_command("get pods -o json")
        assert json.loads(result)["items"][0]["metadata"]["name"] == "sample-pod"


async def test_kubectl_describe(integration_components):
    """Test kubectl describe command through the kubectl executor."""
    _, kubectl_executor, _, _ = integration_components
    
    # Mock the kubectl execution results
    with mock.patch('mcp_server_troubleshoot.kubectl.KubectlExecutor._execute_kubectl') as mock_execute:
        mock_execute.return_value = """
Name:         sample-pod
Namespace:    default
Status:       Running
IP:           10.0.0.1
Containers:
  nginx:
    Image:    nginx:latest
    State:    Running
"""
        
        # Test kubectl describe command
        result = await kubectl_executor.execute_command("describe pod sample-pod")
        assert "Name:         sample-pod" in result
        assert "Status:       Running" in result


async def test_mcp_server_list_tools(integration_components):
    """Test MCP server list_tools functionality."""
    _, _, _, mcp_server = integration_components
    
    # Test list_tools
    tools = mcp_server.list_tools()
    
    # Check if all tools are registered
    tool_names = [tool["name"] for tool in tools]
    assert "bundle__initialize" in tool_names
    assert "kubectl__execute" in tool_names
    assert "files__list_directory" in tool_names
    assert "files__read_file" in tool_names
    assert "files__search_files" in tool_names


async def test_mcp_server_call_tool(integration_components):
    """Test MCP server call_tool functionality with different tools."""
    _, _, _, mcp_server = integration_components
    
    # Test calling files__list_directory tool
    with mock.patch('mcp_server_troubleshoot.files.FileExplorer.list_directory') as mock_list:
        mock_list.return_value = [
            {"name": "kubernetes", "type": "directory"},
            {"name": "kube-apiserver", "type": "directory"}
        ]
        
        result = await mcp_server.call_tool(
            "files__list_directory",
            {"path": "/"}
        )
        
        assert result == [
            {"name": "kubernetes", "type": "directory"},
            {"name": "kube-apiserver", "type": "directory"}
        ]
    
    # Test calling files__read_file tool
    with mock.patch('mcp_server_troubleshoot.files.FileExplorer.read_file') as mock_read:
        mock_read.return_value = "Sample file content"
        
        result = await mcp_server.call_tool(
            "files__read_file",
            {"path": "/kubernetes/pods/sample-pod.yaml"}
        )
        
        assert result == "Sample file content"
    
    # Test calling kubectl__execute tool
    with mock.patch('mcp_server_troubleshoot.kubectl.KubectlExecutor.execute_command') as mock_exec:
        mock_exec.return_value = "kubectl output"
        
        result = await mcp_server.call_tool(
            "kubectl__execute",
            {"command": "get pods"}
        )
        
        assert result == "kubectl output"


async def test_error_handling(integration_components):
    """Test error handling across components."""
    _, kubectl_executor, file_explorer, mcp_server = integration_components
    
    # Test file not found error
    with pytest.raises(FileNotFoundError):
        await file_explorer.read_file("/non-existent-file.txt")
    
    # Test handling of invalid kubectl command
    with mock.patch('mcp_server_troubleshoot.kubectl.KubectlExecutor._execute_kubectl') as mock_execute:
        mock_execute.side_effect = Exception("Invalid command")
        
        with pytest.raises(Exception):
            await kubectl_executor.execute_command("invalid command")
    
    # Test MCP server error handling
    with mock.patch('mcp_server_troubleshoot.server.MCPServer.call_tool') as mock_call:
        mock_call.side_effect = ValueError("Invalid parameter")
        
        with pytest.raises(ValueError):
            await mcp_server.call_tool("files__list_directory", {"invalid": "parameter"})


async def test_end_to_end_workflow(integration_components):
    """Test the entire workflow from bundle initialization to file exploration."""
    bundle_manager, kubectl_executor, file_explorer, mcp_server = integration_components
    
    # Step 1: Ensure bundle is initialized
    assert bundle_manager.initialized_bundle is not None
    
    # Step 2: List root directory
    root_listing = await file_explorer.list_directory("/")
    assert any(item["name"] == "kubernetes" for item in root_listing)
    
    # Step 3: Navigate to kubernetes/pods directory
    pods_listing = await file_explorer.list_directory("/kubernetes/pods")
    assert any(item["name"] == "sample-pod.yaml" for item in pods_listing)
    
    # Step 4: Read pod file
    pod_file = await file_explorer.read_file("/kubernetes/pods/sample-pod.yaml")
    assert "name: sample-pod" in pod_file
    
    # Step 5: Execute kubectl command on the pod
    with mock.patch('mcp_server_troubleshoot.kubectl.KubectlExecutor._execute_kubectl') as mock_execute:
        mock_execute.return_value = json.dumps({"metadata": {"name": "sample-pod"}, "status": {"phase": "Running"}})
        
        kubectl_result = await kubectl_executor.execute_command("get pod sample-pod -o json")
        pod_info = json.loads(kubectl_result)
        assert pod_info["metadata"]["name"] == "sample-pod"
    
    # Step 6: Search for errors in logs
    search_results = await file_explorer.search_files("Error")
    assert any("/kubernetes/logs/sample-pod.log" in match for match in search_results)
    
    # Step 7: Read the log file containing errors
    log_file = await file_explorer.read_file("/kubernetes/logs/sample-pod.log")
    assert "Error: something went wrong" in log_file