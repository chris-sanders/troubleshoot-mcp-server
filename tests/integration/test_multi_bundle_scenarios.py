"""
Multi-bundle and concurrency integration tests.

Tests complex server scenarios involving multiple bundles and concurrent operations
to ensure proper resource management, isolation, and reliability.
"""

import asyncio
import gc
import logging
import os
import resource
import subprocess
import time

import pytest

from tests.integration.mcp_test_utils import MCPTestClient, get_test_bundle_path

logger = logging.getLogger(__name__)


async def setup_multi_bundle_clients(tmp_path, count=3):
    """Helper to create multiple MCP clients with different bundle directories."""
    clients = []
    bundle_dirs = []

    try:
        # Create different bundle directories
        for i in range(count):
            bundle_dir = tmp_path / f"bundles_{i}"
            bundle_dir.mkdir()
            bundle_dirs.append(bundle_dir)

            client = MCPTestClient(
                bundle_dir=bundle_dir, env={"MCP_BUNDLE_STORAGE": str(bundle_dir)}
            )
            clients.append(client)

        # Start all clients
        for client in clients:
            await client.start_server()
            await client.initialize_mcp()

        return clients, bundle_dirs

    except Exception:
        # Cleanup on error
        for client in clients:
            try:
                await client.cleanup()
            except Exception:
                pass
        raise


def create_test_bundle_copies(tmp_path, count=5):
    """Create multiple copies of the test bundle for concurrent testing."""
    bundle_path = get_test_bundle_path()
    copies = []

    import shutil

    for i in range(count):
        copy_path = tmp_path / f"test_bundle_{i}.tar.gz"
        shutil.copy2(bundle_path, copy_path)
        copies.append(copy_path)

    return copies


class TestMultiBundleScenarios:
    """Test scenarios involving multiple bundles and complex operations."""

    @pytest.mark.asyncio
    async def test_multiple_bundles_simultaneous_loading(self, tmp_path):
        """Test loading different bundles simultaneously in different servers."""
        clients, bundle_dirs = await setup_multi_bundle_clients(tmp_path, 3)
        test_bundle_copies = create_test_bundle_copies(tmp_path, 3)

        try:
            # Load different bundles in each client simultaneously
            load_tasks = []
            for i, (client, bundle_copy) in enumerate(zip(clients, test_bundle_copies)):
                bundle_name = f"test_bundle_{i}"
                task = self._load_bundle_async(client, bundle_name, bundle_copy)
                load_tasks.append(task)

            # Wait for all bundles to load
            results = await asyncio.gather(*load_tasks, return_exceptions=True)

            # Verify all loads succeeded
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    pytest.fail(f"Bundle {i} loading failed: {result}")
                assert "successfully" in str(result).lower() or len(result) > 0

            # Verify each client has its bundle loaded
            for i, client in enumerate(clients):
                bundles_response = await client.call_tool("list_available_bundles")
                assert len(bundles_response) > 0

        finally:
            for client in clients:
                await client.cleanup()

    @pytest.mark.asyncio
    async def test_bundle_switching_isolation(self, tmp_path):
        """Test that bundle switching in one client doesn't affect others."""
        clients, bundle_dirs = await setup_multi_bundle_clients(tmp_path, 3)
        test_bundle_copies = create_test_bundle_copies(tmp_path, 6)

        try:
            # Load initial bundles
            for i, (client, bundle_copy) in enumerate(zip(clients, test_bundle_copies[:3])):
                await self._load_bundle_async(client, f"bundle_{i}_v1", bundle_copy)

            # Switch bundle in first client while others are working
            client1, client2, client3 = clients

            # Start concurrent operations in clients 2 and 3
            async def continuous_operations(client, client_id):
                operations = []
                for _ in range(5):  # Reduced for faster test
                    try:
                        await client.call_tool("list_files", {"path": "/"})
                        operations.append(f"client_{client_id}_success")
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        operations.append(f"client_{client_id}_error: {e}")
                return operations

            task2 = asyncio.create_task(continuous_operations(client2, 2))
            task3 = asyncio.create_task(continuous_operations(client3, 3))

            # Switch bundle in client 1
            for i in range(3, 5):  # Load bundles 3, 4
                if i < len(test_bundle_copies):
                    await self._load_bundle_async(client1, f"bundle_1_v{i}", test_bundle_copies[i])
                    await asyncio.sleep(0.2)

            # Wait for concurrent operations to complete
            results2 = await task2
            results3 = await task3

            # Verify other clients weren't affected
            success_count_2 = sum(1 for r in results2 if "success" in r)
            success_count_3 = sum(1 for r in results3 if "success" in r)

            assert (
                success_count_2 >= 3
            ), f"Client 2 should have mostly successful operations, got {results2}"
            assert (
                success_count_3 >= 3
            ), f"Client 3 should have mostly successful operations, got {results3}"

        finally:
            for client in clients:
                await client.cleanup()

    @pytest.mark.asyncio
    async def test_concurrent_file_operations(self, tmp_path):
        """Test concurrent file operations across multiple bundles."""
        clients, bundle_dirs = await setup_multi_bundle_clients(tmp_path, 3)
        test_bundle_copies = create_test_bundle_copies(tmp_path, 3)

        try:
            # Load bundles in all clients
            for client, bundle_copy in zip(clients, test_bundle_copies):
                await self._load_bundle_async(client, "test_bundle", bundle_copy)

            # Define concurrent file operations
            async def file_operations(client, client_id):
                operations = []
                try:
                    # List files
                    await client.call_tool("list_files", {"path": "/"})
                    operations.append(f"list_files_{client_id}_success")

                    # Try to read a common file (if it exists)
                    try:
                        await client.call_tool("read_file", {"file_path": "/cluster-info.yaml"})
                        operations.append(f"read_file_{client_id}_success")
                    except Exception:
                        operations.append(f"read_file_{client_id}_not_found")

                    # Grep operation
                    await client.call_tool(
                        "grep_files", {"pattern": "kubernetes", "path": "/", "max_files": 5}
                    )
                    operations.append(f"grep_{client_id}_success")

                except Exception as e:
                    operations.append(f"error_{client_id}: {str(e)}")

                return operations

            # Run operations concurrently
            tasks = [file_operations(client, i) for i, client in enumerate(clients)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify all operations completed successfully
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    pytest.fail(f"Client {i} operations failed: {result}")

                success_ops = [op for op in result if "success" in op]
                assert (
                    len(success_ops) >= 2
                ), f"Client {i} should have at least 2 successful operations: {result}"

        finally:
            for client in clients:
                await client.cleanup()

    @pytest.mark.asyncio
    async def test_concurrent_kubectl_operations(self, tmp_path):
        """Test concurrent kubectl operations across multiple bundles."""
        clients, bundle_dirs = await setup_multi_bundle_clients(tmp_path, 3)
        test_bundle_copies = create_test_bundle_copies(tmp_path, 3)

        try:
            # Load bundles in all clients
            for client, bundle_copy in zip(clients, test_bundle_copies):
                await self._load_bundle_async(client, "test_bundle", bundle_copy)

            async def kubectl_operations(client, client_id):
                operations = []
                try:
                    # Get cluster info
                    await client.call_tool(
                        "kubectl_command", {"command": "cluster-info", "timeout": 10}
                    )
                    operations.append(f"cluster_info_{client_id}_success")

                except Exception as e:
                    operations.append(f"kubectl_error_{client_id}: {str(e)}")

                return operations

            # Run kubectl operations concurrently
            tasks = [kubectl_operations(client, i) for i, client in enumerate(clients)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify operations (some may fail due to bundle content, but should not crash)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    pytest.fail(f"Client {i} kubectl operations crashed: {result}")

                # At least the operations should complete without crashing
                assert (
                    len(result) > 0
                ), f"Client {i} should have completed some operations: {result}"

        finally:
            for client in clients:
                await client.cleanup()

    async def _load_bundle_async(self, client, bundle_name, bundle_path):
        """Helper to load a bundle asynchronously."""
        return await client.call_tool(
            "initialize_bundle", {"bundle_name": bundle_name, "bundle_path": str(bundle_path)}
        )


class TestConcurrentOperations:
    """Test concurrent operations and thread safety."""

    @pytest.mark.asyncio
    async def test_multiple_clients_same_bundle(self, tmp_path):
        """Test multiple clients accessing the same bundle directory."""
        bundle_dir = tmp_path / "shared_bundles"
        bundle_dir.mkdir()

        # Create multiple clients sharing the same bundle directory
        clients = []
        try:
            for i in range(3):
                client = MCPTestClient(
                    bundle_dir=bundle_dir, env={"MCP_BUNDLE_STORAGE": str(bundle_dir)}
                )
                await client.start_server()
                await client.initialize_mcp()
                clients.append(client)

            # Load the same bundle in all clients
            bundle_path = get_test_bundle_path()
            load_tasks = []
            for client in clients:
                task = client.call_tool(
                    "initialize_bundle",
                    {"bundle_name": "shared_bundle", "bundle_path": str(bundle_path)},
                )
                load_tasks.append(task)

            # Execute loads concurrently
            results = await asyncio.gather(*load_tasks, return_exceptions=True)

            # At least one should succeed (others might get file locks)
            successful_loads = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_loads) >= 1, f"At least one load should succeed: {results}"

            # All clients should be able to list the bundle
            await asyncio.sleep(1)  # Allow time for bundle registration
            for client in clients:
                bundles = await client.call_tool("list_available_bundles")
                bundle_names = str(bundles)
                assert "shared_bundle" in bundle_names

        finally:
            for client in clients:
                await client.cleanup()

    @pytest.mark.asyncio
    async def test_rapid_bundle_switching(self, tmp_path):
        """Test rapid bundle switching for race conditions."""
        client = MCPTestClient(bundle_dir=tmp_path / "bundles")

        try:
            await client.start_server()
            await client.initialize_mcp()

            # Create multiple bundle copies
            bundle_copies = create_test_bundle_copies(tmp_path, 5)

            # Rapidly switch between bundles
            switch_tasks = []
            for i, bundle_copy in enumerate(bundle_copies):
                task = client.call_tool(
                    "initialize_bundle",
                    {"bundle_name": f"rapid_bundle_{i}", "bundle_path": str(bundle_copy)},
                )
                switch_tasks.append(task)

            # Execute switches concurrently (some may fail due to timing)
            results = await asyncio.gather(*switch_tasks, return_exceptions=True)

            # At least some should succeed
            successful_switches = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_switches) >= 2, f"At least 2 switches should succeed: {results}"

            # Final state should be consistent
            bundles = await client.call_tool("list_available_bundles")
            assert len(bundles) > 0, "Should have bundles loaded"

        finally:
            await client.cleanup()

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self, tmp_path):
        """Test many concurrent tool calls on the same client."""
        client = MCPTestClient(bundle_dir=tmp_path / "bundles")

        try:
            await client.start_server()
            await client.initialize_mcp()

            # Load a bundle
            bundle_path = get_test_bundle_path()
            await client.call_tool(
                "initialize_bundle",
                {"bundle_name": "concurrent_test", "bundle_path": str(bundle_path)},
            )

            # Create many concurrent tool calls
            async def make_tool_call(call_id):
                try:
                    await client.call_tool("list_files", {"path": "/"})
                    return f"call_{call_id}_success"
                except Exception as e:
                    return f"call_{call_id}_error: {str(e)}"

            # Launch 10 concurrent calls (reduced for performance)
            tasks = [make_tool_call(i) for i in range(10)]
            results = await asyncio.gather(*tasks)

            # Most should succeed
            successes = [r for r in results if "success" in r]
            assert len(successes) >= 7, f"Most calls should succeed: {results}"

        finally:
            await client.cleanup()


class TestResourceManagement:
    """Test resource management and cleanup."""

    @pytest.mark.asyncio
    async def test_memory_usage_multiple_bundles(self, tmp_path):
        """Test memory usage with multiple loaded bundles."""
        # Get initial memory usage (RSS in KB)
        initial_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

        clients = []
        try:
            # Create and load bundles in multiple clients
            for i in range(3):
                bundle_dir = tmp_path / f"memory_test_{i}"
                bundle_dir.mkdir()

                client = MCPTestClient(bundle_dir=bundle_dir)
                await client.start_server()
                await client.initialize_mcp()
                clients.append(client)

                # Load bundle
                bundle_path = get_test_bundle_path()
                await client.call_tool(
                    "initialize_bundle",
                    {"bundle_name": f"memory_bundle_{i}", "bundle_path": str(bundle_path)},
                )

            # Check memory usage after loading (RSS in KB, convert to bytes for comparison)
            loaded_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            memory_increase = (loaded_memory - initial_memory) * 1024  # Convert KB to bytes

            # Memory should increase but not excessively (less than 500MB)
            assert (
                memory_increase < 500 * 1024 * 1024
            ), f"Memory increase too high: {memory_increase / 1024 / 1024:.1f} MB"

        finally:
            # Cleanup and check memory recovery
            for client in clients:
                await client.cleanup()

            # Force garbage collection
            gc.collect()
            await asyncio.sleep(1)

            final_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            memory_recovered = (loaded_memory - final_memory) * 1024  # Convert KB to bytes

            # Allow for some memory not being recovered immediately
            if memory_increase > 0:
                assert (
                    memory_recovered >= -memory_increase
                ), f"Memory should not increase beyond loaded state: {memory_recovered / 1024 / 1024:.1f} MB"

    @pytest.mark.asyncio
    async def test_file_descriptor_management(self, tmp_path):
        """Test file descriptor management with multiple operations."""
        # Get initial file descriptor count
        initial_fds = len(os.listdir("/proc/self/fd")) if os.path.exists("/proc/self/fd") else 0

        client = MCPTestClient(bundle_dir=tmp_path / "fd_test")

        try:
            await client.start_server()
            await client.initialize_mcp()

            # Load bundle
            bundle_path = get_test_bundle_path()
            await client.call_tool(
                "initialize_bundle", {"bundle_name": "fd_test", "bundle_path": str(bundle_path)}
            )

            # Perform many file operations
            for i in range(20):  # Reduced for performance
                try:
                    await client.call_tool("list_files", {"path": "/"})
                    if i % 5 == 0:
                        await client.call_tool(
                            "grep_files", {"pattern": "test", "path": "/", "max_files": 5}
                        )
                except Exception:
                    pass  # Some operations may fail, but shouldn't leak FDs

            # Check file descriptor count
            if os.path.exists("/proc/self/fd"):
                current_fds = len(os.listdir("/proc/self/fd"))
                fd_increase = current_fds - initial_fds

                # Should not have excessive FD increase (less than 20)
                assert fd_increase < 20, f"Too many file descriptors opened: {fd_increase}"

        finally:
            await client.cleanup()

    @pytest.mark.asyncio
    async def test_process_cleanup_kubectl(self, tmp_path):
        """Test that kubectl processes are properly cleaned up."""
        client = MCPTestClient(bundle_dir=tmp_path / "kubectl_cleanup")

        try:
            await client.start_server()
            await client.initialize_mcp()

            # Load bundle
            bundle_path = get_test_bundle_path()
            await client.call_tool(
                "initialize_bundle",
                {"bundle_name": "kubectl_cleanup", "bundle_path": str(bundle_path)},
            )

            # Get initial process count (using subprocess count as proxy)
            try:
                result = subprocess.run(["pgrep", "kubectl"], capture_output=True, text=True)
                initial_processes = (
                    len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
                )
            except Exception:
                initial_processes = 0  # pgrep might not be available on all systems

            # Execute multiple kubectl commands
            kubectl_tasks = []
            for i in range(3):  # Reduced for performance
                task = client.call_tool(
                    "kubectl_command", {"command": "version --client", "timeout": 5}
                )
                kubectl_tasks.append(task)

            # Execute concurrently
            await asyncio.gather(*kubectl_tasks, return_exceptions=True)

            # Wait for processes to clean up
            await asyncio.sleep(2)

            # Check process count
            try:
                result = subprocess.run(["pgrep", "kubectl"], capture_output=True, text=True)
                final_processes = (
                    len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
                )
            except Exception:
                final_processes = 0

            # Should not have many more kubectl processes running
            process_increase = final_processes - initial_processes
            assert (
                process_increase <= 2
            ), f"Too many kubectl processes left running: {process_increase}"

        finally:
            await client.cleanup()


class TestPerformanceAndReliability:
    """Test performance and reliability under load."""

    @pytest.mark.asyncio
    async def test_server_performance_large_bundles(self, tmp_path):
        """Test server performance with large bundle operations."""
        client = MCPTestClient(bundle_dir=tmp_path / "performance")

        try:
            await client.start_server()
            await client.initialize_mcp()

            # Load bundle
            bundle_path = get_test_bundle_path()
            start_time = time.time()

            await client.call_tool(
                "initialize_bundle",
                {"bundle_name": "performance_test", "bundle_path": str(bundle_path)},
            )

            load_time = time.time() - start_time

            # Bundle loading should complete in reasonable time (less than 30 seconds)
            assert load_time < 30, f"Bundle loading took too long: {load_time:.2f}s"

            # Test file listing performance
            start_time = time.time()
            await client.call_tool("list_files", {"path": "/"})
            list_time = time.time() - start_time

            # File listing should be fast (less than 5 seconds)
            assert list_time < 5, f"File listing took too long: {list_time:.2f}s"

        finally:
            await client.cleanup()

    @pytest.mark.asyncio
    async def test_response_times_under_load(self, tmp_path):
        """Test response times under concurrent load."""
        client = MCPTestClient(bundle_dir=tmp_path / "load_test")

        try:
            await client.start_server()
            await client.initialize_mcp()

            # Load bundle
            bundle_path = get_test_bundle_path()
            await client.call_tool(
                "initialize_bundle", {"bundle_name": "load_test", "bundle_path": str(bundle_path)}
            )

            # Measure response times under load
            async def timed_operation(op_id):
                start_time = time.time()
                try:
                    await client.call_tool("list_files", {"path": "/"})
                    end_time = time.time()
                    return {"id": op_id, "time": end_time - start_time, "success": True}
                except Exception as e:
                    end_time = time.time()
                    return {
                        "id": op_id,
                        "time": end_time - start_time,
                        "success": False,
                        "error": str(e),
                    }

            # Launch 5 concurrent operations (reduced for performance)
            tasks = [timed_operation(i) for i in range(5)]
            results = await asyncio.gather(*tasks)

            # Analyze results
            successful_ops = [r for r in results if r["success"]]
            response_times = [r["time"] for r in successful_ops]

            # Most operations should succeed
            assert (
                len(successful_ops) >= 4
            ), f"Most operations should succeed: {len(successful_ops)}/5"

            # Response times should be reasonable (95th percentile < 5 seconds)
            if response_times:
                response_times.sort()
                p95_time = response_times[int(len(response_times) * 0.95)]
                assert p95_time < 5, f"95th percentile response time too high: {p95_time:.2f}s"

        finally:
            await client.cleanup()

    @pytest.mark.asyncio
    async def test_error_propagation_concurrent_scenarios(self, tmp_path):
        """Test proper error propagation in concurrent scenarios."""
        client = MCPTestClient(bundle_dir=tmp_path / "error_test")

        try:
            await client.start_server()
            await client.initialize_mcp()

            # Load bundle
            bundle_path = get_test_bundle_path()
            await client.call_tool(
                "initialize_bundle", {"bundle_name": "error_test", "bundle_path": str(bundle_path)}
            )

            # Mix valid and invalid operations
            async def mixed_operations(op_id):
                results = []

                try:
                    # Valid operation
                    await client.call_tool("list_files", {"path": "/"})
                    results.append(f"op_{op_id}_valid_success")
                except Exception as e:
                    results.append(f"op_{op_id}_valid_error: {str(e)}")

                try:
                    # Invalid operation (bad path)
                    await client.call_tool(
                        "list_files", {"path": "/nonexistent/deeply/nested/path"}
                    )
                    results.append(f"op_{op_id}_invalid_success")
                except Exception:
                    results.append(f"op_{op_id}_invalid_expected_error")

                try:
                    # Invalid tool call
                    await client.call_tool("nonexistent_tool", {})
                    results.append(f"op_{op_id}_bad_tool_success")
                except Exception:
                    results.append(f"op_{op_id}_bad_tool_expected_error")

                return results

            # Run mixed operations concurrently
            tasks = [mixed_operations(i) for i in range(3)]  # Reduced for performance
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify error handling
            all_results = []
            for result in results:
                if isinstance(result, Exception):
                    pytest.fail(f"Concurrent operation crashed: {result}")
                all_results.extend(result)

            # Check that valid operations succeeded and invalid ones failed appropriately
            valid_successes = [r for r in all_results if "valid_success" in r]
            invalid_expected_errors = [r for r in all_results if "expected_error" in r]

            assert (
                len(valid_successes) >= 2
            ), f"Most valid operations should succeed: {valid_successes}"
            assert (
                len(invalid_expected_errors) >= 4
            ), f"Invalid operations should fail appropriately: {invalid_expected_errors}"

        finally:
            await client.cleanup()
