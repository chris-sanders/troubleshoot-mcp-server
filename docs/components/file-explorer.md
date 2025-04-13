# Component: File Explorer

## Purpose
The File Explorer provides file system operations for exploring and examining the contents of support bundles, allowing AI models to discover, access, and search through log files and other bundle artifacts within Kubernetes support bundles.

## Responsibilities
- List files and directories within the bundle, with recursive capability
- Read file contents with line range filtering and binary file detection
- Search for patterns across files with advanced options like case sensitivity and glob patterns
- Ensure file access is contained within the bundle boundaries
- Prevent directory traversal attacks
- Format file operation results with rich metadata
- Detect and handle binary files appropriately

## Interfaces

### Input

#### List Files
- **path**: Path within the bundle to list
- **recursive**: Whether to list recursively (includes subdirectories)

#### Read File
- **path**: Path to the file within the bundle
- **start_line**: Line to start reading from (0-indexed)
- **end_line**: Line to end reading at (0-indexed)

#### Grep Files (Search)
- **pattern**: Regular expression pattern to search for
- **path**: Base path within the bundle to search
- **recursive**: Whether to search recursively
- **glob_pattern**: Pattern for filtering files to search (e.g., "*.log")
- **case_sensitive**: Whether the search is case-sensitive
- **max_results**: Maximum number of results to return

### Output

#### List Files Result
- **entries**: Array of FileEntry objects with metadata:
  - name, path, type, size, modified, accessed, is_binary
- **path**: Base path that was listed
- **recursive**: Whether the listing was recursive
- **total_files**: Count of files found
- **total_dirs**: Count of directories found

#### Read File Result
- **content**: Content of the file (text or hex dump for binary)
- **path**: Path to the file that was read
- **binary**: Whether the file is binary
- **start_line**: First line returned (0-indexed)
- **end_line**: Last line returned (0-indexed)
- **total_lines**: Total number of lines in the file

#### Grep Result
- **matches**: Array of GrepMatch objects:
  - path, line_number, line, match_start, match_end
- **pattern**: The pattern that was searched for
- **path**: Base path that was searched
- **glob_pattern**: File pattern filter used
- **case_sensitive**: Whether search was case-sensitive
- **total_matches**: Total number of matches found
- **files_searched**: Number of files searched
- **truncated**: Whether results were truncated

## Error Handling

The File Explorer implements comprehensive error handling:

- **PathNotFoundError**: When the specified path doesn't exist
- **AccessDeniedError**: When path access is denied for security reasons
- **DirectoryTraversalError**: When path contains directory traversal attempts
- **NotADirectoryError**: When trying to list a file as a directory
- **NotAFileError**: When trying to read a directory as a file
- **InvalidPatternError**: When grep pattern is invalid

## Implementation

### Key Methods

```python
async def list_files(self, path: str, recursive: bool = False) -> ListFilesResult:
    """List files and directories in the given path."""
    
async def read_file(
    self, path: str, start_line: int = 0, end_line: Optional[int] = None
) -> ReadFileResult:
    """Read a file from the bundle with optional line range."""
    
async def grep_files(
    self,
    pattern: str,
    path: str,
    recursive: bool = True,
    glob_pattern: Optional[str] = None,
    case_sensitive: bool = False,
    max_results: int = 1000,
) -> GrepResult:
    """Search for a pattern in files within the bundle."""
```

### Path Security

The File Explorer validates paths to prevent directory traversal:

```python
def _validate_path(self, path: str) -> Path:
    """
    Validate and normalize a path within the bundle.
    Prevents directory traversal attacks.
    """
    # Normalize the path and ensure it's within the bundle directory
    normalized_path = os.path.normpath(path)
    if normalized_path.startswith("..") or "/." in normalized_path:
        raise SecurityError(f"Path '{path}' contains directory traversal")
        
    # Resolve the full path and check it's within the bundle
    full_path = self._bundle_path / normalized_path.lstrip("/")
    
    # Check the resolved path is still within the bundle
    if not str(full_path).startswith(str(self._bundle_path)):
        raise SecurityError(f"Path '{path}' resolves outside the bundle")
        
    return full_path
```

### Binary File Detection

The File Explorer detects binary files:

```python
def _is_binary(self, path: Path) -> bool:
    """
    Check if a file is binary by reading the first chunk of data.
    """
    try:
        with open(path, 'rb') as f:
            chunk = f.read(4096)
            return b'\0' in chunk or detect_encoding(chunk) is None
    except Exception:
        # If we can't determine, assume it's not binary
        return False
```

## Sample Usage

```python
# Create file explorer with bundle manager
bundle_manager = BundleManager(Path("/data/bundles"))
file_explorer = FileExplorer(bundle_manager)

# List files in a directory
list_result = await file_explorer.list_files("/kubernetes/logs", recursive=False)
print(f"Found {list_result.total_files} files and {list_result.total_dirs} directories")

# Read a file
read_result = await file_explorer.read_file("/kubernetes/logs/kube-system/kube-apiserver.log", start_line=100, end_line=150)
print(f"Read {read_result.end_line - read_result.start_line + 1} lines from {read_result.path}")

# Search for patterns
grep_result = await file_explorer.grep_files(
    pattern="Error",
    path="/kubernetes/logs",
    recursive=True,
    glob_pattern="*.log",
    case_sensitive=False
)
print(f"Found {grep_result.total_matches} matches across {grep_result.files_searched} files")
```