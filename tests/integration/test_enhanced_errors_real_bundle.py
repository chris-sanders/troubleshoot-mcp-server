"""
Integration tests for enhanced error messages using real bundle fixtures.

These tests verify that the enhanced error message functionality works
correctly with real support bundle structures.
"""

import pytest
import pytest_asyncio
from pathlib import Path
import tempfile

from troubleshoot_mcp_server.bundle import BundleManager
from troubleshoot_mcp_server.files import (
    FileExplorer,
    DirectoryAccessError,
    ReadFileError,
)

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def bundle_with_realistic_structure(test_support_bundle):
    """
    Create a bundle manager with a realistic structure that includes
    directories with corresponding files that have common extensions.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        bundle_dir = Path(temp_dir)
        manager = BundleManager(bundle_dir)

        # Initialize with the test support bundle
        await manager.initialize_bundle(str(test_support_bundle))

        # Get the active bundle path
        bundle = manager.get_active_bundle()
        bundle_path = bundle.path

        # Create realistic structure similar to what users report
        # Create cluster-resources/pods directory structure
        pods_dir = bundle_path / "cluster-resources" / "pods"
        pods_dir.mkdir(parents=True, exist_ok=True)

        # Create kube-system directory (what user tries to read)
        kube_system_dir = pods_dir / "kube-system"
        kube_system_dir.mkdir(exist_ok=True)

        # Create the corresponding files that should be suggested
        kube_system_json = pods_dir / "kube-system.json"
        kube_system_json.write_text("""{
  "kind": "PodList",
  "apiVersion": "v1",
  "items": [
    {
      "metadata": {
        "name": "coredns-558bd4d5db-abcde",
        "namespace": "kube-system"
      },
      "spec": {
        "containers": [
          {
            "name": "coredns",
            "image": "registry.k8s.io/coredns/coredns:v1.10.1"
          }
        ]
      }
    }
  ]
}""")

        kube_system_yaml = pods_dir / "kube-system.yaml"
        kube_system_yaml.write_text("""kind: PodList
apiVersion: v1
items:
- metadata:
    name: coredns-558bd4d5db-abcde
    namespace: kube-system
  spec:
    containers:
    - name: coredns
      image: registry.k8s.io/coredns/coredns:v1.10.1
""")

        # Create logs structure
        logs_dir = bundle_path / "logs"
        logs_dir.mkdir(exist_ok=True)

        # Create application directory that user might try to read
        application_dir = logs_dir / "application"
        application_dir.mkdir(exist_ok=True)

        # Create corresponding log file
        application_log = logs_dir / "application.log"
        application_log.write_text("""2023-12-01 10:00:00.123 INFO [main] Application starting...
2023-12-01 10:00:01.456 INFO [main] Configuration loaded from /etc/app/config.yaml
2023-12-01 10:00:02.789 INFO [main] Database connection established
2023-12-01 10:00:03.012 INFO [main] Application ready to serve requests
2023-12-01 10:15:22.345 WARN [pool-1] Connection timeout, retrying...
2023-12-01 10:15:23.678 INFO [pool-1] Connection restored
""")

        yield manager


@pytest.mark.asyncio
async def test_realistic_kube_system_directory_error(bundle_with_realistic_structure):
    """
    Test the exact scenario reported by users:
    trying to read 'cluster-resources/pods/kube-system' directory.
    """
    explorer = FileExplorer(bundle_with_realistic_structure)

    # This is the exact path users report having issues with
    with pytest.raises(DirectoryAccessError) as exc_info:
        await explorer.read_file("cluster-resources/pods/kube-system")

    error = exc_info.value
    error_msg = str(error)

    # Verify the error message contains expected components
    assert "Path is not a file: cluster-resources/pods/kube-system" in error_msg
    assert "Did you mean one of these files?" in error_msg

    # Verify both JSON and YAML files are suggested
    assert "cluster-resources/pods/kube-system.json" in error_msg
    assert "cluster-resources/pods/kube-system.yaml" in error_msg

    # Verify suggestions are available programmatically
    assert len(error.suggestions) == 2
    assert "cluster-resources/pods/kube-system.json" in error.suggestions
    assert "cluster-resources/pods/kube-system.yaml" in error.suggestions


@pytest.mark.asyncio
async def test_application_logs_directory_error(bundle_with_realistic_structure):
    """
    Test another common scenario: trying to read a logs directory.
    """
    explorer = FileExplorer(bundle_with_realistic_structure)

    # Try to read the application directory in logs
    with pytest.raises(DirectoryAccessError) as exc_info:
        await explorer.read_file("logs/application")

    error = exc_info.value
    error_msg = str(error)

    # Verify the error message format
    assert "Path is not a file: logs/application" in error_msg
    assert "Did you mean one of these files?" in error_msg
    assert "logs/application.log" in error_msg

    # Verify suggestion is available
    assert len(error.suggestions) == 1
    assert "logs/application.log" in error.suggestions


@pytest.mark.asyncio
async def test_suggested_files_are_actually_readable(bundle_with_realistic_structure):
    """
    Verify that the files suggested in error messages can actually be read.
    """
    explorer = FileExplorer(bundle_with_realistic_structure)

    # Get suggestions from the error
    with pytest.raises(DirectoryAccessError) as exc_info:
        await explorer.read_file("cluster-resources/pods/kube-system")

    # Try to read each suggested file
    for suggestion in exc_info.value.suggestions:
        result = await explorer.read_file(suggestion)

        # Verify the file can be read and contains expected content
        assert result.path == suggestion
        assert len(result.content) > 0
        assert result.binary is False

        # Verify content makes sense for the file type
        if suggestion.endswith(".json"):
            assert '"kind": "PodList"' in result.content
        elif suggestion.endswith(".yaml"):
            assert "kind: PodList" in result.content


@pytest.mark.asyncio
async def test_no_false_suggestions_for_unrelated_directories(bundle_with_realistic_structure):
    """
    Verify that directories without matching files don't get false suggestions.
    """
    explorer = FileExplorer(bundle_with_realistic_structure)
    bundle = bundle_with_realistic_structure.get_active_bundle()

    # Create a directory without any matching files
    empty_dir = bundle.path / "empty-namespace"
    empty_dir.mkdir(exist_ok=True)

    # Try to read it - should fall back to standard error
    with pytest.raises(ReadFileError) as exc_info:
        await explorer.read_file("empty-namespace")

    # Should be a plain ReadFileError, not DirectoryAccessError
    error = exc_info.value
    assert not isinstance(error, DirectoryAccessError)
    assert str(error) == "Path is not a file: empty-namespace"


@pytest.mark.asyncio
async def test_multiple_extension_suggestions_ordered_correctly(bundle_with_realistic_structure):
    """
    Test that when multiple extensions are available, they are suggested in a consistent order.
    """
    explorer = FileExplorer(bundle_with_realistic_structure)
    bundle = bundle_with_realistic_structure.get_active_bundle()
    bundle_path = bundle.path

    # Create a directory with multiple extension files
    multi_dir = bundle_path / "config"
    multi_dir.mkdir(exist_ok=True)

    settings_dir = multi_dir / "settings"
    settings_dir.mkdir(exist_ok=True)

    # Create files with different extensions in various orders
    settings_txt = multi_dir / "settings.txt"
    settings_txt.write_text("Setting: value")

    settings_json = multi_dir / "settings.json"
    settings_json.write_text('{"setting": "value"}')

    settings_yaml = multi_dir / "settings.yaml"
    settings_yaml.write_text("setting: value")

    # Try to read the directory
    with pytest.raises(DirectoryAccessError) as exc_info:
        await explorer.read_file("config/settings")

    error = exc_info.value
    suggestions = error.suggestions

    # Should have all three suggestions
    assert len(suggestions) == 3

    # Verify all expected files are suggested
    assert "config/settings.json" in suggestions
    assert "config/settings.yaml" in suggestions
    assert "config/settings.txt" in suggestions


@pytest.mark.asyncio
async def test_error_message_integration_with_real_paths(bundle_with_realistic_structure):
    """
    Test the complete error message integration with realistic bundle paths.
    """
    explorer = FileExplorer(bundle_with_realistic_structure)

    # Test with a path that has a single suggestion
    with pytest.raises(DirectoryAccessError) as exc_info:
        await explorer.read_file("logs/application")

    error_msg = str(exc_info.value)

    # Verify the complete message format matches specification
    expected_lines = [
        "Path is not a file: logs/application",
        "",
        "Did you mean one of these files?",
        "• logs/application.log",
    ]

    for line in expected_lines:
        assert line in error_msg, f"Expected line '{line}' not found in: {error_msg}"

    # Verify proper bullet point formatting
    assert "• logs/application.log" in error_msg

    # Verify it's not suggesting non-existent files
    assert "• logs/application.json" not in error_msg
    assert "• logs/application.yaml" not in error_msg
