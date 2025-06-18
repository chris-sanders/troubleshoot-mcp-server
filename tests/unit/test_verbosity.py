"""
Unit tests for the verbosity system and ResponseFormatter.
"""

import json
import os
import unittest
from unittest.mock import patch

from src.mcp_server_troubleshoot.formatters import ResponseFormatter, VerbosityLevel, get_formatter
from src.mcp_server_troubleshoot.bundle import BundleMetadata, BundleFileInfo
from src.mcp_server_troubleshoot.files import (
    FileInfo,
    FileListResult,
    FileContentResult,
    GrepResult,
    GrepMatch,
)
from src.mcp_server_troubleshoot.kubectl import KubectlResult
from pathlib import Path


class TestVerbositySystem(unittest.TestCase):
    """Test the verbosity system functionality."""

    def setUp(self):
        """Set up test data."""
        self.bundle_metadata = BundleMetadata(
            id="test-bundle-123",
            source="test-bundle.tar.gz",
            path=Path("/tmp/test-bundle"),
            kubeconfig_path=Path("/tmp/test-bundle/kubeconfig"),
            initialized=True,
        )

        self.bundle_info = BundleFileInfo(
            path="/data/bundles/test-bundle.tar.gz",
            relative_path="test-bundle.tar.gz",
            name="test-bundle.tar.gz",
            size_bytes=1048576,
            modified_time=1640995200.0,
            valid=True,
            validation_message=None,
        )

        self.file_info = FileInfo(
            name="config.yaml",
            path="/kubernetes/config.yaml",
            type="file",
            size=2048,
            access_time=1640995200.0,
            modify_time=1640995200.0,
            is_binary=False,
        )

        self.file_list_result = FileListResult(
            path="/kubernetes",
            entries=[self.file_info],
            recursive=False,
            total_files=1,
            total_dirs=0,
        )

        self.file_content_result = FileContentResult(
            path="/kubernetes/config.yaml",
            content="apiVersion: v1\nkind: Config",
            start_line=0,
            end_line=1,
            total_lines=2,
            binary=False,
        )

        self.grep_match = GrepMatch(
            path="/kubernetes/config.yaml",
            line_number=0,
            line="apiVersion: v1",
            match="apiVersion",
            offset=0,
        )

        self.grep_result = GrepResult(
            pattern="apiVersion",
            path="/kubernetes",
            glob_pattern=None,
            matches=[self.grep_match],
            total_matches=1,
            files_searched=1,
            case_sensitive=False,
            truncated=False,
        )

        self.kubectl_result = KubectlResult(
            command="get pods",
            exit_code=0,
            stdout="NAME   READY   STATUS\npod1   1/1     Running",
            stderr="",
            output={"items": [{"metadata": {"name": "pod1"}}]},
            is_json=True,
            duration_ms=150,
        )

    def test_verbosity_enum(self):
        """Test verbosity level enum values."""
        self.assertEqual(VerbosityLevel.MINIMAL, "minimal")
        self.assertEqual(VerbosityLevel.STANDARD, "standard")
        self.assertEqual(VerbosityLevel.VERBOSE, "verbose")
        self.assertEqual(VerbosityLevel.DEBUG, "debug")

    def test_formatter_initialization(self):
        """Test ResponseFormatter initialization."""
        # Test with explicit verbosity
        formatter = ResponseFormatter("minimal")
        self.assertEqual(formatter.verbosity, VerbosityLevel.MINIMAL)

        # Test with invalid verbosity defaults to minimal
        formatter = ResponseFormatter("invalid")
        self.assertEqual(formatter.verbosity, VerbosityLevel.MINIMAL)

        # Test with None uses environment variable (verbose in tests)
        formatter = ResponseFormatter(None)
        self.assertEqual(formatter.verbosity, VerbosityLevel.VERBOSE)  # Due to test environment

    @patch.dict(os.environ, {"MCP_VERBOSITY": "debug"})
    def test_formatter_environment_variable(self):
        """Test formatter respects MCP_VERBOSITY environment variable."""
        formatter = ResponseFormatter()
        self.assertEqual(formatter.verbosity, VerbosityLevel.DEBUG)

    @patch.dict(os.environ, {"MCP_DEBUG": "true"})
    def test_formatter_debug_flag(self):
        """Test formatter respects MCP_DEBUG environment variable."""
        formatter = ResponseFormatter()
        self.assertEqual(formatter.verbosity, VerbosityLevel.DEBUG)

    def test_get_formatter_function(self):
        """Test the get_formatter convenience function."""
        formatter = get_formatter("verbose")
        self.assertEqual(formatter.verbosity, VerbosityLevel.VERBOSE)

        formatter = get_formatter()
        self.assertEqual(formatter.verbosity, VerbosityLevel.VERBOSE)  # Due to test environment

    def test_bundle_initialization_formatting(self):
        """Test bundle initialization response formatting."""
        # Test minimal format
        formatter = ResponseFormatter("minimal")
        response = formatter.format_bundle_initialization(self.bundle_metadata, True)
        parsed = json.loads(response)
        self.assertIn("bundle_id", parsed)
        self.assertIn("status", parsed)
        self.assertEqual(parsed["status"], "ready")

        # Test with API server unavailable
        response = formatter.format_bundle_initialization(self.bundle_metadata, False)
        parsed = json.loads(response)
        self.assertEqual(parsed["status"], "api_unavailable")

        # Test standard format
        formatter = ResponseFormatter("standard")
        response = formatter.format_bundle_initialization(self.bundle_metadata, True)
        parsed = json.loads(response)
        self.assertIn("source", parsed)
        self.assertIn("initialized", parsed)

        # Test verbose format
        formatter = ResponseFormatter("verbose")
        response = formatter.format_bundle_initialization(self.bundle_metadata, True)
        self.assertIn("Bundle initialized successfully", response)
        self.assertIn("```json", response)

    def test_bundle_list_formatting(self):
        """Test bundle list response formatting."""
        bundles = [self.bundle_info]

        # Test minimal format
        formatter = ResponseFormatter("minimal")
        response = formatter.format_bundle_list(bundles)
        parsed = json.loads(response)
        self.assertIsInstance(parsed, list)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0], "test-bundle.tar.gz")

        # Test standard format
        formatter = ResponseFormatter("standard")
        response = formatter.format_bundle_list(bundles)
        parsed = json.loads(response)
        self.assertIn("bundles", parsed)
        self.assertIn("count", parsed)
        self.assertEqual(parsed["count"], 1)

        # Test verbose format
        formatter = ResponseFormatter("verbose")
        response = formatter.format_bundle_list(bundles)
        self.assertIn("```json", response)
        self.assertIn("Usage Instructions", response)

        # Test empty list
        formatter = ResponseFormatter("minimal")
        response = formatter.format_bundle_list([])
        parsed = json.loads(response)
        self.assertEqual(parsed, [])

    def test_file_list_formatting(self):
        """Test file list response formatting."""
        # Test minimal format
        formatter = ResponseFormatter("minimal")
        response = formatter.format_file_list(self.file_list_result)
        parsed = json.loads(response)
        self.assertIsInstance(parsed, list)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0], "config.yaml")

        # Test standard format
        formatter = ResponseFormatter("standard")
        response = formatter.format_file_list(self.file_list_result)
        parsed = json.loads(response)
        self.assertIn("files", parsed)
        self.assertIn("count", parsed)

        # Test verbose format
        formatter = ResponseFormatter("verbose")
        response = formatter.format_file_list(self.file_list_result)
        self.assertIn("Listed files in", response)
        self.assertIn("Directory metadata", response)

    def test_file_content_formatting(self):
        """Test file content response formatting."""
        # Test minimal format
        formatter = ResponseFormatter("minimal")
        response = formatter.format_file_content(self.file_content_result)
        self.assertEqual(response, self.file_content_result.content)

        # Test standard format
        formatter = ResponseFormatter("standard")
        response = formatter.format_file_content(self.file_content_result)
        self.assertIn("File content", response)
        self.assertIn("lines", response)

        # Test verbose format
        formatter = ResponseFormatter("verbose")
        response = formatter.format_file_content(self.file_content_result)
        self.assertIn("Read text file", response)
        self.assertIn("```", response)

        # Test binary file
        binary_result = FileContentResult(
            path="/bin/data",
            content="0000: 48 65 6c 6c 6f",
            start_line=0,
            end_line=0,
            total_lines=1,
            binary=True,
        )

        formatter = ResponseFormatter("minimal")
        response = formatter.format_file_content(binary_result)
        self.assertEqual(response, binary_result.content)

        formatter = ResponseFormatter("verbose")
        response = formatter.format_file_content(binary_result)
        self.assertIn("Read binary file", response)

    def test_grep_results_formatting(self):
        """Test grep results response formatting."""
        # Test minimal format (ultra-compact)
        formatter = ResponseFormatter("minimal")
        response = formatter.format_grep_results(self.grep_result)
        parsed = json.loads(response)

        # Should be a compact result object with matches array
        self.assertIsInstance(parsed, dict)
        self.assertIn("matches", parsed)
        matches = parsed["matches"]
        self.assertEqual(len(matches), 1)

        # Each match should have file, line, and content (not just match)
        match = matches[0]
        self.assertIn("file", match)
        self.assertIn("line", match)
        self.assertIn("content", match)  # Full line content instead of just match
        self.assertEqual(match["file"], "/kubernetes/config.yaml")
        self.assertEqual(match["line"], 1)  # 1-indexed
        self.assertEqual(match["content"], "apiVersion: v1")  # Full line

        # Should use compact JSON format (no pretty-printing)
        # Verify it's using compact separators by checking structure
        self.assertTrue(response.startswith('{"matches":['))
        self.assertNotIn("}\n", response)  # No newlines
        self.assertNotIn("  ", response)  # No double spaces for indentation

        # Test standard format
        formatter = ResponseFormatter("standard")
        response = formatter.format_grep_results(self.grep_result)
        parsed = json.loads(response)
        self.assertIn("matches", parsed)
        self.assertIn("total", parsed)
        self.assertIn("files_searched", parsed)

        # Test verbose format
        formatter = ResponseFormatter("verbose")
        response = formatter.format_grep_results(self.grep_result)
        self.assertIn("Found 1 matches", response)
        self.assertIn("**File:", response)
        self.assertIn("Search metadata", response)

        # Test no matches
        no_matches_result = GrepResult(
            pattern="notfound",
            path="/kubernetes",
            glob_pattern=None,
            matches=[],
            total_matches=0,
            files_searched=1,
            case_sensitive=False,
            truncated=False,
        )

        formatter = ResponseFormatter("minimal")
        response = formatter.format_grep_results(no_matches_result)
        parsed = json.loads(response)
        # Should be a compact result object with empty matches array
        self.assertIsInstance(parsed, dict)
        self.assertIn("matches", parsed)
        self.assertEqual(parsed["matches"], [])

    def test_kubectl_result_formatting(self):
        """Test kubectl result response formatting."""
        # Test minimal format
        formatter = ResponseFormatter("minimal")
        response = formatter.format_kubectl_result(self.kubectl_result)
        parsed = json.loads(response)
        self.assertIn("items", parsed)

        # Test standard format
        formatter = ResponseFormatter("standard")
        response = formatter.format_kubectl_result(self.kubectl_result)
        parsed = json.loads(response)
        self.assertIn("output", parsed)
        self.assertIn("exit_code", parsed)

        # Test verbose format
        formatter = ResponseFormatter("verbose")
        response = formatter.format_kubectl_result(self.kubectl_result)
        self.assertIn("kubectl command executed successfully", response)
        self.assertIn("Command metadata", response)

        # Test non-JSON output
        text_result = KubectlResult(
            command="describe pod",
            exit_code=0,
            stdout="Name: pod1\nNamespace: default",
            stderr="",
            output="Name: pod1\nNamespace: default",
            is_json=False,
            duration_ms=200,
        )

        formatter = ResponseFormatter("minimal")
        response = formatter.format_kubectl_result(text_result)
        self.assertEqual(response, text_result.stdout)

    def test_error_formatting(self):
        """Test error message formatting."""
        error_msg = "This is a test error message\nWith multiple lines\nAnd more details"
        diagnostics = {"error": "test", "details": "additional info"}

        # Test minimal format
        formatter = ResponseFormatter("minimal")
        response = formatter.format_error(error_msg)
        self.assertEqual(response, "This is a test error message")

        # Test standard format
        formatter = ResponseFormatter("standard")
        response = formatter.format_error(error_msg)
        lines = response.split("\n")
        self.assertEqual(len(lines), 3)

        # Test verbose format
        formatter = ResponseFormatter("verbose")
        response = formatter.format_error(error_msg)
        self.assertEqual(response, error_msg)

        # Test debug format with diagnostics
        formatter = ResponseFormatter("debug")
        response = formatter.format_error(error_msg, diagnostics)
        self.assertIn(error_msg, response)
        self.assertIn("Diagnostic information", response)
        self.assertIn("```json", response)

    def test_token_savings(self):
        """Test that minimal format provides significant token savings."""
        bundles = [self.bundle_info]

        verbose_formatter = ResponseFormatter("verbose")
        minimal_formatter = ResponseFormatter("minimal")

        verbose_response = verbose_formatter.format_bundle_list(bundles)
        minimal_response = minimal_formatter.format_bundle_list(bundles)

        # Calculate approximate token savings (4 chars per token)
        verbose_tokens = len(verbose_response) / 4
        minimal_tokens = len(minimal_response) / 4
        savings_percentage = ((verbose_tokens - minimal_tokens) / verbose_tokens) * 100

        # Should achieve at least 30% token reduction
        self.assertGreaterEqual(
            savings_percentage, 30.0, f"Token savings {savings_percentage:.1f}% below 30% target"
        )

        # Verify minimal response is actually smaller
        self.assertLess(len(minimal_response), len(verbose_response))

    def test_file_size_formatting(self):
        """Test file size formatting helper."""
        formatter = ResponseFormatter("minimal")

        # Test different file sizes
        self.assertEqual(formatter._format_file_size(512), "512 B")
        self.assertEqual(formatter._format_file_size(1536), "1.5 KB")
        self.assertEqual(formatter._format_file_size(2097152), "2.0 MB")
        self.assertEqual(formatter._format_file_size(1073741824), "1.0 GB")


if __name__ == "__main__":
    unittest.main()
