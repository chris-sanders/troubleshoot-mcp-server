# AsyncIO Testing Best Practices

This project uses asyncio for asynchronous operations and pytest-asyncio for testing. This document provides detailed guidance on properly handling asyncio in tests to avoid common pitfalls and warnings.

## Asyncio Configuration

We've carefully configured pytest-asyncio for optimal test behavior:

1. **Event Loop Settings**
   - `asyncio_mode = "strict"` - Enforces proper test declaration with `@pytest.mark.asyncio` 
   - `asyncio_default_fixture_loop_scope = "function"` - Provides test isolation with a new loop per test
   - `asyncio_default_test_loop_scope = "function"` - Ensures consistent loop behavior

2. **Warning Management**
   - We use targeted warning filters with detailed comments explaining why each warning can't be fixed
   - We avoid blanket suppressions (e.g., never use `ignore::DeprecationWarning`)
   - All suppressed warnings are documented with specific reasons

## Clean Asyncio Fixture

The `clean_asyncio` fixture provides a properly isolated and cleaned event loop for tests:

```python
@pytest.fixture
def clean_asyncio():
    """Provides a clean event loop for each test with proper resource cleanup."""
    import asyncio
    import gc
    
    # Create a new event loop for test isolation
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    yield loop
    
    # Clean up resources after the test
    try:
        # Cancel all pending tasks
        pending = asyncio.all_tasks(loop)
        if pending:
            for task in pending:
                task.cancel()
            loop.run_until_complete(
                asyncio.gather(*pending, return_exceptions=True)
            )
            
        # Properly shut down async generators
        if hasattr(loop, 'shutdown_asyncgens'):
            loop.run_until_complete(loop.shutdown_asyncgens())
        
        # Close the loop properly
        loop.close()
        
    except (RuntimeError, asyncio.CancelledError) as e:
        import logging
        logging.getLogger("tests").debug(f"Controlled exception during event loop cleanup: {e}")
    
    # Create a new event loop for the next test
    asyncio.set_event_loop(asyncio.new_event_loop())
    
    # Force garbage collection to clean up any lingering objects
    gc.collect()
```

## Writing Proper Asyncio Tests

Follow these guidelines when writing asyncio tests:

1. **Test Behavior, Not Implementation**
   - Focus on testing the observable behavior of the function
   - Avoid testing internal implementation details like task creation
   - Use high-level assertions about results, not how they were achieved

2. **Proper Test Declaration**
   - Always use `@pytest.mark.asyncio` for async tests
   - Explicitly include the `clean_asyncio` fixture when testing complex async code

3. **Resource Management**
   - Use context managers or explicit cleanup for resources
   - Avoid creating long-running tasks that outlive the test
   - Test should clean up all resources they create 

4. **Mocking Asyncio Components**
   - Use `AsyncMock` from `unittest.mock` for mocking coroutines
   - Create proper async context managers for testing context-dependent code
   - When testing code that uses `asyncio.create_subprocess_exec()`, provide proper mock objects with async methods

## Handling Remaining Warnings

Some warnings are unavoidable due to third-party libraries or pytest-asyncio behavior:

1. **Pytest-asyncio Plugin Warning**
   - Warning: `PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.`
   - Reason: This comes from pytest-asyncio's internal implementation and can be safely ignored
   - Fix: We've properly set the configuration, but the plugin still generates the warning

2. **Unix Pipe Transport Warning**
   - Warning: `PytestUnraisableExceptionWarning: Exception ignored in _UnixReadPipeTransport.__del__`
   - Reason: This is from the Python standard library's asyncio implementation
   - Fix: We've added a targeted filter for this specific warning

## Testing Guidelines for Specific Components

1. **Bundle Manager**
   - Test initialization, downloading, and cleanup behavior
   - Mock external processes and subprocess calls
   - Focus on testing the public API, not internal implementation

2. **File Explorer**
   - Test listing files, reading content, and error handling
   - Verify directory traversal behavior and security measures
   - Use temporary directories with controlled test data

3. **Server Components**
   - Test request handling and response generation
   - Verify proper error handling and status codes
   - Mock dependencies for isolated testing