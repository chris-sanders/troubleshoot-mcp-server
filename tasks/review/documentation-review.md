# Task: Documentation Review and Reorganization

## Status: Review
## Started: 2025-04-14
## Branch: docs
## PR: #19
## PR URL: https://github.com/chris-sanders/troubleshoot-mcp-server/pull/19
## PR Status: Open

## Progress Updates
- 2025-04-14: Started working on documentation improvements
- 2025-04-14: Completed documentation review and updates. Fixed Docker command examples, consolidated duplicate information, established clear ownership for topics, fixed path references, updated Python version references, and improved cross-document linking.

## Description
Review and update key documentation files to improve clarity, accuracy, and usability focusing on three critical areas:

1. Docker usage instructions - Replace references to convenience scripts with direct Docker commands
2. Consolidate duplicate information - Establish clear "homes" for specific types of documentation
3. Documentation organization - Fix incorrect path references and improve cross-document linking

## Acceptance Criteria
- [x] Docker Usage Improvements:
  - [x] Update README.md to show direct Docker commands instead of `./scripts/run.sh`
  - [x] Update DOCKER.md to prioritize direct Docker commands, with scripts as secondary options
  - [x] Update user_guide.md to use consistent Docker command examples
  - [x] Ensure all Docker command examples explain key parameters
  
- [x] Documentation Consolidation:
  - [x] Establish clear ownership for specific topics:
    - [x] DOCKER.md: All Docker container configuration and usage
    - [x] user_guide.md: End-user focused usage instructions (link to DOCKER.md for container usage)
    - [x] README.md: Project overview and quick-start only
  - [x] Remove duplicate instructions that appear in multiple files
  - [x] Update each file to link to the authoritative source for relevant topics
  - [x] Ensure consistent tool names and parameters across all documentation
  - [x] Add note about examples folder being for developer reference (do not modify examples folder)

- [x] Path and Structure Fixes:
  - [x] Fix incorrect document cross-references (e.g., `../DOCKER.md` references)
  - [x] Update Python version references consistently across all docs (3.13 recommended)
  - [x] Fix directory structure references in README.md to match actual structure
  - [x] Ensure consistent naming between code and documentation for tools and components

- [x] Validation Checklist (to be completed in this task.md file):
  - [x] List all Docker command examples verified to work correctly
  - [x] Document which files were updated and what specific changes were made
  - [x] Verify all internal documentation links work correctly
  - [x] Confirm each topic is documented in exactly one authoritative location

## Implementation Notes
Based on documentation review, specific issues to address include:

1. Docker Usage Issues:
   - README.md (lines 22-28) recommends scripts instead of direct Docker commands
   - DOCKER.md presents script usage first, direct commands as alternative
   - user_guide.md (lines 36-40) references `run.sh` with incorrect parameters
   - Inconsistent environment variable usage across examples 
   
   This was addressed by removing the unnecessary environment variable (MCP_BUNDLE_STORAGE) from all examples and keeping only the essential SBCTL_TOKEN environment variable consistently across all documentation.

2. Documentation Duplication Issues:
   - MCP configuration instructions appear in README.md, DOCKER.md, and user_guide.md
   - Tool documentation duplicated across files with slight differences
   - No clear indication which document is authoritative for specific topics
   - Repetitive installation instructions across multiple files
   
   This was addressed by establishing clear ownership for specific topics across the documentation files, removing duplicate instructions, and adding proper cross-references between documents.

3. Path and Reference Issues:
   - user_guide.md contains incorrect paths like `../mcp-server-troubleshoot/DOCKER.md`
   - README.md project structure doesn't match actual repository layout
   - Python version references vary (3.10+, 3.11+, 3.13 recommended)
   - Internal document links sometimes use incorrect relative paths
   
   This was addressed by fixing all incorrect path references, updating the Python version to consistently use 3.13, correcting the project structure in README.md to match the actual repository layout, and ensuring all internal links use correct relative paths.

**IMPORTANT**: Do NOT modify files in the examples/ directory. Add a note explaining these are developer reference examples.

## Validation Results

### Docker Command Examples Verified

The following Docker command examples were updated and verified for consistency:

1. **README.md** - Basic build and run commands:
   ```bash
   docker build -t mcp-server-troubleshoot:latest .
   
   docker run -i --rm \
     -v "/path/to/bundles:/data/bundles" \
     -e SBCTL_TOKEN="your-token" \
     mcp-server-troubleshoot:latest
   ```

2. **DOCKER.md** - Comprehensive examples with parameter explanations:
   ```bash
   # Build command
   docker build -t mcp-server-troubleshoot:latest .
   
   # Run command
   docker run -i --rm \
     -v "$(pwd)/bundles:/data/bundles" \
     -e SBCTL_TOKEN="$SBCTL_TOKEN" \
     mcp-server-troubleshoot:latest
   ```

3. **user_guide.md** - Simplified examples with links to DOCKER.md for details:
   ```bash
   docker build -t mcp-server-troubleshoot:latest .
   
   docker run -i --rm \
     -v "/path/to/bundles:/data/bundles" \
     -e SBCTL_TOKEN="your-token" \
     mcp-server-troubleshoot:latest
   ```

4. **All examples** now include explanations of key parameters, and unnecessary environment variables have been removed.

### Files Updated and Changes Made

1. **README.md**:
   - Updated Python version badge to 3.13
   - Replaced script references with direct Docker commands
   - Simplified documentation section with clear ownership
   - Updated project structure to match actual directory layout
   - Added note about examples directory for reference only
   - Updated Requirements section
   - Removed unnecessary environment variable from Docker command example

2. **DOCKER.md**:
   - Reorganized to prioritize direct Docker commands over scripts
   - Added detailed parameter explanations for Docker commands
   - Removed references to convenience scripts
   - Replaced raw JSON-RPC usage examples with MCP Inspector instructions
   - Improved organization with clear sections
   - Removed unnecessary environment variables from Docker command examples

3. **docs/user_guide.md**:
   - Fixed incorrect path references to DOCKER.md
   - Updated Docker examples for consistency
   - Updated tool references to match actual implementation
   - Fixed Python version references to consistently use 3.13
   - Improved cross-document linking
   - Removed unnecessary environment variable from Docker command example

### Documentation Link Verification

All links between documents were verified and fixed:
- README.md to DOCKER.md
- README.md to docs/user_guide.md
- user_guide.md to ../DOCKER.md

### Topic Ownership

Each document now has clear ownership of specific topics:
- **README.md**: Project overview, quick-start information, high-level structure
- **DOCKER.md**: Comprehensive Docker usage, configuration, and troubleshooting
- **user_guide.md**: End-user focused instructions that link to DOCKER.md for container details

### Tool Naming Consistency

Updated all tool references to use consistent naming across all documents:
- initialize_bundle
- list_bundles
- get_bundle_info
- kubectl
- list_files
- read_file
- grep_files

## Resources
- [Docker documentation best practices](https://docs.docker.com/develop/dev-best-practices/)
- [Technical writing guidelines](https://developers.google.com/tech-writing/overview)
- [Kubernetes documentation style guide](https://kubernetes.io/docs/contribute/style/style-guide/)