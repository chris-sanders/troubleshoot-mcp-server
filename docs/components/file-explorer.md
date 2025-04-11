# Component: File Explorer

## Purpose
The File Explorer provides file system operations for exploring and examining the contents of support bundles, allowing AI models to discover, access, and search through log files and other bundle artifacts.

## Responsibilities
- List files and directories within the bundle
- Read file contents, optionally with line range filtering
- Search for patterns across files (similar to grep)
- Ensure file access is contained within the bundle
- Prevent directory traversal attacks
- Format file operation results for consumption by AI models

## Interfaces
- **Input**: Operation type, path within bundle, operation-specific parameters
- **Output**: Formatted operation results (file listings, file contents, search results)

## Dependencies
- Bundle Manager for bundle path information
- File system access for reading files and directories
- Search capabilities for pattern matching

## Design Decisions
- Implement separate functions for different file operations (list, read, search) to match common CLI paradigms
- Add safety measures to prevent access outside the bundle directory
- Support line range filtering for reading large files
- Implement search functionality similar to grep for familiar pattern matching
- Normalize paths to prevent directory traversal
- Provide detailed error messages for failed operations
- Format results consistently for easy consumption

## Examples

```python
# List files in a directory
result = file_explorer.list_files("logs/kube-system")

# Read a file with line range
result = file_explorer.read_file(
    "logs/kube-system/kube-apiserver.log",
    start_line=100,
    end_line=150
)

# Search for a pattern
result = file_explorer.grep_files(
    "Error",
    "logs/kube-system/*.log"
)
```