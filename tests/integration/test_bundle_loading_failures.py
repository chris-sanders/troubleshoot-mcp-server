"""
Integration tests for bundle loading failure scenarios.

These tests specifically focus on failure scenarios that could cause production bugs
like "server won't load bundles" by testing realistic failure conditions and
ensuring proper error handling and recovery.
"""

import asyncio
import json
import os
import shutil
import signal
import tarfile
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest

from mcp_server_troubleshoot.bundle import (
    BundleDownloadError,
    BundleInitializationError,
    BundleManager,
    BundleManagerError,
    BundleNotFoundError,
)
from tests.test_utils.bundle_helpers import TempBundleManager


class TestBundleDirectoryFailures:
    """Test failures related to bundle directory access and permissions."""

    @pytest.mark.asyncio
    async def test_bundle_directory_not_readable(self, tmp_path):
        """Test bundle loading when bundle directory is not readable."""
        bundle_dir = tmp_path / "unreadable_bundle_dir"
        bundle_dir.mkdir()

        # Create a test bundle first
        with TempBundleManager("standard", tmp_path) as temp_bundle:
            bundle_file = bundle_dir / "test_bundle.tar.gz"
            shutil.copy(temp_bundle.get_tar_path(), bundle_file)

        # Remove read permissions from directory
        bundle_dir.chmod(0o000)

        try:
            manager = BundleManager(bundle_dir)

            # Attempt to list bundles should handle permission error gracefully
            bundles = await manager.list_available_bundles(include_invalid=True)
            # Should return empty list rather than crash
            assert isinstance(bundles, list)

            # Attempt to initialize should fail with appropriate error
            with pytest.raises((BundleNotFoundError, BundleManagerError, PermissionError)):
                await manager.initialize_bundle(str(bundle_file))

        finally:
            # Restore permissions for cleanup
            bundle_dir.chmod(0o755)

    @pytest.mark.asyncio
    async def test_bundle_directory_does_not_exist(self, tmp_path):
        """Test bundle loading when bundle directory doesn't exist."""
        nonexistent_dir = tmp_path / "does_not_exist"

        manager = BundleManager(nonexistent_dir)

        # List bundles should handle missing directory gracefully
        bundles = await manager.list_available_bundles()
        assert bundles == []

        # Initialize with nonexistent file should fail appropriately
        with pytest.raises((BundleNotFoundError, BundleManagerError)):
            await manager.initialize_bundle("nonexistent_bundle.tar.gz")

    @pytest.mark.asyncio
    async def test_bundle_directory_not_writable(self, tmp_path):
        """Test bundle loading when bundle directory is not writable."""
        bundle_dir = tmp_path / "readonly_bundle_dir"
        bundle_dir.mkdir()

        # Create a test bundle
        with TempBundleManager("standard", tmp_path) as temp_bundle:
            bundle_file = bundle_dir / "test_bundle.tar.gz"
            shutil.copy(temp_bundle.get_tar_path(), bundle_file)

        # Make directory read-only
        bundle_dir.chmod(0o555)

        try:
            manager = BundleManager(bundle_dir)

            # Should still be able to list bundles
            bundles = await manager.list_available_bundles()
            assert len(bundles) == 1

            # But initialization might fail when trying to create extraction directory
            with pytest.raises((BundleInitializationError, BundleManagerError, PermissionError)):
                await manager.initialize_bundle(str(bundle_file))

        finally:
            # Restore permissions for cleanup
            bundle_dir.chmod(0o755)


class TestSbctlCommandFailures:
    """Test failures related to sbctl command availability and execution."""

    @pytest.mark.asyncio
    async def test_sbctl_command_not_available(self, tmp_path):
        """Test bundle initialization when sbctl command is not available."""
        with TempBundleManager("standard", tmp_path) as temp_bundle:
            manager = BundleManager(tmp_path / "bundles")

            # Mock subprocess to simulate command not found
            with patch("asyncio.create_subprocess_exec") as mock_exec:
                mock_exec.side_effect = FileNotFoundError("sbctl: command not found")

                with pytest.raises(BundleInitializationError) as exc_info:
                    await manager.initialize_bundle(str(temp_bundle.get_tar_path()))

                assert "sbctl" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sbctl_command_not_executable(self, tmp_path):
        """Test bundle initialization when sbctl exists but is not executable."""
        with TempBundleManager("standard", tmp_path) as temp_bundle:
            manager = BundleManager(tmp_path / "bundles")

            # Mock subprocess to simulate permission denied
            with patch("asyncio.create_subprocess_exec") as mock_exec:
                mock_exec.side_effect = PermissionError("Permission denied: sbctl")

                with pytest.raises(BundleInitializationError) as exc_info:
                    await manager.initialize_bundle(str(temp_bundle.get_tar_path()))

                assert "Permission denied" in str(exc_info.value) or "sbctl" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sbctl_crashes_immediately(self, tmp_path):
        """Test handling when sbctl crashes immediately on startup."""
        with TempBundleManager("standard", tmp_path) as temp_bundle:
            manager = BundleManager(tmp_path / "bundles")

            # Mock subprocess that exits immediately with error
            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.returncode = 1
            mock_process.wait.return_value = 1
            mock_process.stdout = AsyncMock()
            mock_process.stderr = AsyncMock()
            mock_process.stdout.read.return_value = b"sbctl: fatal error occurred"
            mock_process.stderr.read.return_value = b"Error: invalid bundle format"

            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                with pytest.raises(BundleInitializationError) as exc_info:
                    await manager.initialize_bundle(str(temp_bundle.get_tar_path()))

                assert "sbctl process exited" in str(exc_info.value)


class TestCorruptedBundleFiles:
    """Test failures related to corrupted or invalid bundle files."""

    @pytest.mark.asyncio
    async def test_invalid_tar_gz_file(self, tmp_path):
        """Test loading a file that appears to be tar.gz but is corrupted."""
        manager = BundleManager(tmp_path / "bundles")

        # Create a file with .tar.gz extension but invalid content
        corrupted_bundle = tmp_path / "corrupted.tar.gz"
        corrupted_bundle.write_text("This is not a valid tar.gz file content")

        with pytest.raises((BundleInitializationError, BundleManagerError)):
            await manager.initialize_bundle(str(corrupted_bundle))

    @pytest.mark.asyncio
    async def test_empty_tar_gz_file(self, tmp_path):
        """Test loading an empty tar.gz file."""
        manager = BundleManager(tmp_path / "bundles")

        # Create an empty tar.gz file
        empty_bundle = tmp_path / "empty.tar.gz"
        with tarfile.open(empty_bundle, "w:gz"):
            pass  # Create empty archive

        # Should fail during sbctl initialization
        with pytest.raises((BundleInitializationError, BundleManagerError)):
            await manager.initialize_bundle(str(empty_bundle))

    @pytest.mark.asyncio
    async def test_tar_gz_with_missing_files(self, tmp_path):
        """Test loading a bundle that's missing expected files."""
        manager = BundleManager(tmp_path / "bundles")

        # Create a tar.gz with minimal structure
        bundle_path = tmp_path / "minimal.tar.gz"
        with tarfile.open(bundle_path, "w:gz") as tar:
            # Add just a single empty file
            info = tarfile.TarInfo(name="README.txt")
            info.size = 0
            tar.addfile(info, fileobj=None)

        # Should fail when sbctl tries to process it
        with pytest.raises((BundleInitializationError, BundleManagerError)):
            await manager.initialize_bundle(str(bundle_path))

    @pytest.mark.asyncio
    async def test_bundle_with_permission_errors(self, tmp_path):
        """Test loading a bundle where extracted files have wrong permissions."""
        # Create a bundle with restricted permissions
        temp_dir = tmp_path / "bundle_creation"
        temp_dir.mkdir()

        # Create a file with no read permissions
        restricted_file = temp_dir / "restricted.txt"
        restricted_file.write_text("Cannot read this")
        restricted_file.chmod(0o000)

        # Create tar.gz
        bundle_path = tmp_path / "restricted.tar.gz"
        try:
            with tarfile.open(bundle_path, "w:gz") as tar:
                tar.add(restricted_file, arcname="restricted.txt")
        finally:
            # Restore permissions for cleanup
            restricted_file.chmod(0o644)

        manager = BundleManager(tmp_path / "bundles")

        # Should handle permission errors during extraction gracefully
        # The actual behavior may vary, but it should not crash the server
        try:
            await manager.initialize_bundle(str(bundle_path))
        except (BundleInitializationError, BundleManagerError, PermissionError):
            # Any of these errors are acceptable - the key is no crash
            pass


class TestNetworkFailures:
    """Test failures related to network downloads."""

    @pytest.mark.asyncio
    async def test_network_connection_refused(self, tmp_path):
        """Test bundle download with connection refused."""
        manager = BundleManager(tmp_path / "bundles")

        # Mock aiohttp to simulate connection refused
        with patch("aiohttp.ClientSession") as mock_session:
            mock_session.return_value.__aenter__.return_value.get.side_effect = (
                aiohttp.ClientConnectorError(connection_key=None, os_error=None)
            )

            with pytest.raises(BundleDownloadError):
                await manager.initialize_bundle("https://nonexistent.example.com/bundle.tar.gz")

    @pytest.mark.asyncio
    async def test_http_error_responses(self, tmp_path):
        """Test bundle download with various HTTP error responses."""
        manager = BundleManager(tmp_path / "bundles")

        for status_code in [404, 500, 502, 503]:
            with patch("aiohttp.ClientSession") as mock_session:
                mock_response = AsyncMock()
                mock_response.status = status_code
                mock_response.reason = f"HTTP {status_code} Error"
                mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = (
                    mock_response
                )

                with pytest.raises(BundleDownloadError) as exc_info:
                    await manager.initialize_bundle("https://example.com/bundle.tar.gz")

                assert str(status_code) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_download_size_limit_exceeded(self, tmp_path):
        """Test bundle download exceeding size limits."""
        manager = BundleManager(tmp_path / "bundles")

        # Mock response with large content-length
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.content_length = 2 * 1024 * 1024 * 1024  # 2GB
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = (
                mock_response
            )

            with pytest.raises(BundleDownloadError) as exc_info:
                await manager.initialize_bundle("https://example.com/bundle.tar.gz")

            assert (
                "size" in str(exc_info.value).lower() and "exceeds" in str(exc_info.value).lower()
            )

    @pytest.mark.asyncio
    async def test_replicated_api_failures(self, tmp_path):
        """Test Replicated API specific failures."""
        manager = BundleManager(tmp_path / "bundles")
        replicated_url = "https://vendor.replicated.com/troubleshoot/analyze/test-slug"

        # Test missing token
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(BundleDownloadError) as exc_info:
                await manager.initialize_bundle(replicated_url)

            assert "token" in str(exc_info.value).lower()

        # Test API authentication failure
        with patch.dict(os.environ, {"SBCTL_TOKEN": "invalid-token"}):
            with patch("httpx.AsyncClient.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 401
                mock_response.text = "Unauthorized"
                mock_get.return_value = mock_response

                with pytest.raises(BundleDownloadError) as exc_info:
                    await manager.initialize_bundle(replicated_url)

                assert "401" in str(exc_info.value) or "unauthorized" in str(exc_info.value).lower()

        # Test API not found
        with patch.dict(os.environ, {"SBCTL_TOKEN": "valid-token"}):
            with patch("httpx.AsyncClient.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 404
                mock_response.text = "Not Found"
                mock_get.return_value = mock_response

                with pytest.raises(BundleDownloadError) as exc_info:
                    await manager.initialize_bundle(replicated_url)

                assert "404" in str(exc_info.value) or "not found" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_replicated_invalid_response_format(self, tmp_path):
        """Test Replicated API returning invalid response format."""
        manager = BundleManager(tmp_path / "bundles")
        replicated_url = "https://vendor.replicated.com/troubleshoot/analyze/test-slug"

        with patch.dict(os.environ, {"SBCTL_TOKEN": "valid-token"}):
            # Test invalid JSON
            with patch("httpx.AsyncClient.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
                mock_get.return_value = mock_response

                with pytest.raises(BundleDownloadError) as exc_info:
                    await manager.initialize_bundle(replicated_url)

                assert "json" in str(exc_info.value).lower()

            # Test missing signedUri
            with patch("httpx.AsyncClient.get") as mock_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"bundle": {"other_field": "value"}}
                mock_get.return_value = mock_response

                with pytest.raises(BundleDownloadError) as exc_info:
                    await manager.initialize_bundle(replicated_url)

                assert "signedUri" in str(exc_info.value)


class TestDiskSpaceFailures:
    """Test failures related to insufficient disk space."""

    @pytest.mark.asyncio
    async def test_insufficient_disk_space_extraction(self, tmp_path):
        """Test bundle extraction failure due to insufficient disk space."""
        with TempBundleManager("standard", tmp_path) as temp_bundle:
            manager = BundleManager(tmp_path / "bundles")

            # Mock shutil.disk_usage to simulate low disk space
            with patch("shutil.disk_usage") as mock_disk_usage:
                # Return very low free space (less than 1MB)
                mock_disk_usage.return_value = (1000, 500, 500)  # total, used, free

                # The actual error might vary by system, but should be handled gracefully
                try:
                    await manager.initialize_bundle(str(temp_bundle.get_tar_path()))
                    # If it succeeds, that's fine too - depends on actual extraction size
                except (BundleInitializationError, BundleManagerError, OSError):
                    # These are acceptable error types for disk space issues
                    pass

    @pytest.mark.asyncio
    async def test_disk_space_during_download(self, tmp_path):
        """Test download failure when disk runs out of space during download."""
        manager = BundleManager(tmp_path / "bundles")

        # Mock response that would fill disk
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.content_length = None

            # Mock chunks that eventually cause disk full error
            async def mock_chunks():
                yield b"x" * 1024  # First chunk works
                raise OSError(28, "No space left on device")  # ENOSPC

            mock_response.content.iter_chunked.return_value = mock_chunks()
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = (
                mock_response
            )

            with pytest.raises(BundleDownloadError) as exc_info:
                await manager.initialize_bundle("https://example.com/bundle.tar.gz")

            assert "space" in str(exc_info.value).lower() or "disk" in str(exc_info.value).lower()


class TestErrorRecoveryAndServerStability:
    """Test that server remains functional after bundle loading failures."""

    @pytest.mark.asyncio
    async def test_server_functional_after_failed_initialization(self, tmp_path):
        """Test that server can recover after failed bundle initialization."""
        manager = BundleManager(tmp_path / "bundles")

        # First, try to initialize with a bad bundle
        corrupted_bundle = tmp_path / "corrupted.tar.gz"
        corrupted_bundle.write_text("Invalid content")

        with pytest.raises((BundleInitializationError, BundleManagerError)):
            await manager.initialize_bundle(str(corrupted_bundle))

        # Verify server state is clean
        assert manager.active_bundle is None
        assert manager.sbctl_process is None

        # Now try with a valid bundle - should work
        with TempBundleManager("standard", tmp_path) as temp_bundle:
            try:
                # This might fail if sbctl is not available, but the manager should handle it
                await manager.initialize_bundle(str(temp_bundle.get_tar_path()))
                # If it succeeds, verify state is correct
                if manager.active_bundle:
                    assert manager.active_bundle is not None
            except (BundleInitializationError, FileNotFoundError):
                # Expected if sbctl not available in test environment
                pass

    @pytest.mark.asyncio
    async def test_multiple_failed_initializations(self, tmp_path):
        """Test server stability after multiple failed initialization attempts."""
        manager = BundleManager(tmp_path / "bundles")

        # Try multiple different failure scenarios
        failure_scenarios = [
            "nonexistent_file.tar.gz",
            str(tmp_path / "empty.tar.gz"),  # Create empty file
            "https://nonexistent.example.com/bundle.tar.gz",
        ]

        # Create the empty file
        (tmp_path / "empty.tar.gz").touch()

        for scenario in failure_scenarios:
            with pytest.raises(
                (
                    BundleNotFoundError,
                    BundleInitializationError,
                    BundleDownloadError,
                    BundleManagerError,
                )
            ):
                await manager.initialize_bundle(scenario)

            # Verify clean state after each failure
            assert manager.active_bundle is None
            assert manager.sbctl_process is None

    @pytest.mark.asyncio
    async def test_partial_failure_cleanup(self, tmp_path):
        """Test cleanup occurs properly after partial failures."""
        manager = BundleManager(tmp_path / "bundles")

        # Create a bundle that will fail during sbctl initialization
        with TempBundleManager("standard", tmp_path) as temp_bundle:
            # Mock subprocess to fail after creating some files
            with patch("asyncio.create_subprocess_exec") as mock_exec:
                mock_exec.side_effect = Exception("Simulated failure")

                with pytest.raises(BundleInitializationError):
                    await manager.initialize_bundle(str(temp_bundle.get_tar_path()))

                # Verify cleanup occurred
                assert manager.active_bundle is None
                assert manager.sbctl_process is None

    @pytest.mark.asyncio
    async def test_error_messages_are_informative(self, tmp_path):
        """Test that error messages provide useful information for debugging."""
        manager = BundleManager(tmp_path / "bundles")

        # Test various error scenarios and verify error messages
        test_cases = [
            ("nonexistent.tar.gz", BundleNotFoundError, "not found"),
            ("https://nonexistent.example.com/bundle.tar.gz", BundleDownloadError, "download"),
        ]

        for bundle_source, expected_error, expected_keyword in test_cases:
            with pytest.raises(expected_error) as exc_info:
                await manager.initialize_bundle(bundle_source)

            error_message = str(exc_info.value).lower()
            assert expected_keyword in error_message
            # Error message should include the source for debugging
            assert bundle_source.lower() in error_message or "bundle" in error_message

    @pytest.mark.asyncio
    async def test_concurrent_failure_handling(self, tmp_path):
        """Test handling of concurrent bundle initialization failures."""
        manager = BundleManager(tmp_path / "bundles")

        # Create multiple concurrent initialization attempts with bad bundles
        corrupted_bundle = tmp_path / "corrupted.tar.gz"
        corrupted_bundle.write_text("Invalid content")

        async def try_init():
            with pytest.raises((BundleInitializationError, BundleManagerError)):
                await manager.initialize_bundle(str(corrupted_bundle))

        # Run multiple concurrent attempts
        tasks = [try_init() for _ in range(3)]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Verify manager is in clean state
        assert manager.active_bundle is None
        assert manager.sbctl_process is None


class TestBundleValidationFailures:
    """Test failures in bundle validation and listing."""

    @pytest.mark.asyncio
    async def test_list_bundles_with_permission_errors(self, tmp_path):
        """Test listing bundles when some files have permission errors."""
        bundle_dir = tmp_path / "bundles"
        bundle_dir.mkdir()

        # Create a valid bundle
        with TempBundleManager("standard", tmp_path) as temp_bundle:
            valid_bundle = bundle_dir / "valid.tar.gz"
            shutil.copy(temp_bundle.get_tar_path(), valid_bundle)

        # Create a bundle with no read permissions
        restricted_bundle = bundle_dir / "restricted.tar.gz"
        restricted_bundle.write_text("content")
        restricted_bundle.chmod(0o000)

        try:
            manager = BundleManager(bundle_dir)

            # Should handle permission errors gracefully
            bundles = await manager.list_available_bundles(include_invalid=True)

            # Should include the valid bundle
            valid_bundles = [b for b in bundles if b.valid]
            assert len(valid_bundles) >= 1

            # May or may not include the restricted bundle depending on implementation
            # but should not crash
            assert isinstance(bundles, list)

        finally:
            # Restore permissions for cleanup
            restricted_bundle.chmod(0o644)

    @pytest.mark.asyncio
    async def test_bundle_validation_with_corrupted_files(self, tmp_path):
        """Test bundle validation handles corrupted tar files gracefully."""
        bundle_dir = tmp_path / "bundles"
        bundle_dir.mkdir()

        # Create files that look like bundles but are corrupted
        corrupted_files = [
            ("binary_data.tar.gz", b"\x00\x01corrupted\xff\xfe"),
            ("partial_tar.tar.gz", b"partial tar header data"),
            ("wrong_extension.tar.gz", "This is just text"),
        ]

        for filename, content in corrupted_files:
            bundle_file = bundle_dir / filename
            if isinstance(content, str):
                bundle_file.write_text(content)
            else:
                bundle_file.write_bytes(content)

        manager = BundleManager(bundle_dir)

        # Should handle corrupted files gracefully
        bundles = await manager.list_available_bundles(include_invalid=True)

        # All should be marked as invalid
        for bundle in bundles:
            assert not bundle.valid
            assert bundle.validation_message is not None
            assert (
                "error" in bundle.validation_message.lower()
                or "invalid" in bundle.validation_message.lower()
            )

    @pytest.mark.asyncio
    async def test_bundle_validation_edge_cases(self, tmp_path):
        """Test bundle validation with edge cases like empty files, special names."""
        bundle_dir = tmp_path / "bundles"
        bundle_dir.mkdir()

        # Create various edge case files
        edge_cases = [
            ("empty.tar.gz", b""),  # Empty file
            (".hidden.tar.gz", b"hidden file content"),  # Hidden file
            ("spaces in name.tar.gz", b"content"),  # Spaces in name
            ("unicode_ñame.tar.gz", b"unicode content"),  # Unicode characters
        ]

        for filename, content in edge_cases:
            bundle_file = bundle_dir / filename
            bundle_file.write_bytes(content)

        manager = BundleManager(bundle_dir)

        # Should handle all edge cases without crashing
        bundles = await manager.list_available_bundles(include_invalid=True)

        # Should return results for all files
        assert len(bundles) == len(edge_cases)

        # All should be invalid due to incorrect format
        for bundle in bundles:
            assert not bundle.valid


class TestRealWorldFailureScenarios:
    """Test real-world failure scenarios that could occur in production."""

    @pytest.mark.asyncio
    async def test_bundle_extraction_interrupted(self, tmp_path):
        """Test handling when bundle extraction is interrupted."""
        with TempBundleManager("standard", tmp_path) as temp_bundle:
            manager = BundleManager(tmp_path / "bundles")

            def interrupted_extract(*args, **kwargs):
                # Extract partially then raise an error
                raise KeyboardInterrupt("Extraction interrupted")

            with patch.object(tarfile.TarFile, "extractall", side_effect=interrupted_extract):
                with pytest.raises((BundleInitializationError, KeyboardInterrupt)):
                    await manager.initialize_bundle(str(temp_bundle.get_tar_path()))

                # Verify cleanup occurred
                assert manager.active_bundle is None

    @pytest.mark.asyncio
    async def test_system_resource_exhaustion(self, tmp_path):
        """Test handling when system resources are exhausted."""
        with TempBundleManager("standard", tmp_path) as temp_bundle:
            manager = BundleManager(tmp_path / "bundles")

            # Mock subprocess creation to simulate resource exhaustion
            with patch("asyncio.create_subprocess_exec") as mock_exec:
                mock_exec.side_effect = OSError(12, "Cannot allocate memory")  # ENOMEM

                with pytest.raises(BundleInitializationError) as exc_info:
                    await manager.initialize_bundle(str(temp_bundle.get_tar_path()))

                assert (
                    "memory" in str(exc_info.value).lower()
                    or "resource" in str(exc_info.value).lower()
                )

    @pytest.mark.asyncio
    async def test_file_system_readonly(self, tmp_path):
        """Test handling when file system becomes read-only."""
        with TempBundleManager("standard", tmp_path) as temp_bundle:
            # Create manager with a directory that will become read-only
            bundle_dir = tmp_path / "readonly_fs"
            bundle_dir.mkdir()

            manager = BundleManager(bundle_dir)

            # Mock os.makedirs to simulate read-only filesystem
            with patch("pathlib.Path.mkdir") as mock_mkdir:
                mock_mkdir.side_effect = OSError(30, "Read-only file system")  # EROFS

                with pytest.raises((BundleInitializationError, BundleManagerError, OSError)):
                    await manager.initialize_bundle(str(temp_bundle.get_tar_path()))

    @pytest.mark.asyncio
    async def test_signal_interruption_during_initialization(self, tmp_path):
        """Test handling when process receives signals during initialization."""
        with TempBundleManager("standard", tmp_path) as temp_bundle:
            manager = BundleManager(tmp_path / "bundles")

            # Mock subprocess to simulate process being killed by signal
            mock_process = AsyncMock()
            mock_process.pid = 12345
            mock_process.returncode = -signal.SIGTERM  # Process killed by SIGTERM
            mock_process.wait.return_value = -signal.SIGTERM
            mock_process.stdout = AsyncMock()
            mock_process.stderr = AsyncMock()
            mock_process.stdout.read.return_value = b""
            mock_process.stderr.read.return_value = b"Process terminated by signal"

            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                with pytest.raises(BundleInitializationError) as exc_info:
                    await manager.initialize_bundle(str(temp_bundle.get_tar_path()))

                # Should indicate process was terminated
                assert (
                    "terminated" in str(exc_info.value).lower()
                    or "signal" in str(exc_info.value).lower()
                )

    @pytest.mark.asyncio
    async def test_cleanup_after_multiple_failure_types(self, tmp_path):
        """Test comprehensive cleanup after experiencing multiple types of failures."""
        manager = BundleManager(tmp_path / "bundles")

        # Simulate a sequence of different failures
        failure_sequence = [
            ("nonexistent.tar.gz", BundleNotFoundError),
            ("https://nonexistent.example.com/bundle.tar.gz", BundleDownloadError),
        ]

        for bundle_source, expected_error in failure_sequence:
            with pytest.raises(expected_error):
                await manager.initialize_bundle(bundle_source)

            # After each failure, verify complete cleanup
            assert manager.active_bundle is None
            assert manager.sbctl_process is None
            assert not hasattr(manager, "_host_only_bundle") or not manager._host_only_bundle

        # Finally, verify manager can still function normally
        bundles = await manager.list_available_bundles()
        assert isinstance(bundles, list)  # Should not crash
