# API Reference

This document provides a comprehensive reference for the MCP Server for Kubernetes Support Bundles API.

## Table of Contents

- [MCP Protocol Overview](#mcp-protocol-overview)
- [Bundle Management](#bundle-management)
- [Kubectl Commands](#kubectl-commands)
- [File Operations](#file-operations)
- [Error Handling](#error-handling)

## MCP Protocol Overview

The MCP Server communicates using the Model Context Protocol (MCP), a JSON-based protocol for AI model tools. This section covers the protocol basics.

### Request Format

```json
{
  "name": "tool_name",
  "input": {
    "parameter1": "value1",
    "parameter2": "value2"
  }
}
```

### Response Format

```json
{
  "content": [
    {
      "type": "text",
      "text": "Response content in text format"
    }
  ]
}
```

### Error Response Format

```json
{
  "error": {
    "message": "Error message",
    "type": "ErrorType"
  }
}
```

## Bundle Management

These tools enable management of Kubernetes support bundles.

### initialize_bundle

Initializes (downloads and extracts) a support bundle for use.

**Request:**
```json
{
  "name": "initialize_bundle",
  "input": {
    "source": "https://vendor.replicated.com/troubleshoot/analyze/2024-04-11@08:15",
    "force": false
  }
}
```

**Response:**
```json
{
  "content": [
    {
      "type": "text",
      "text": "Bundle initialized successfully:\n```json\n{\n  \"path\": \"/data/bundles/bundle-2024-04-11-08-15\",\n  \"kubeconfig_path\": \"/tmp/kubeconfig-bundle-2024-04-11-08-15\",\n  \"source\": \"https://vendor.replicated.com/troubleshoot/analyze/2024-04-11@08:15\",\n  \"api_server_pid\": 12345,\n  \"initialized_at\": \"2025-04-12T10:15:30Z\"\n}\n```"
    }
  ]
}
```

**Errors:**
- `AuthenticationError`: If the SBCTL_TOKEN is invalid or missing
- `BundleNotFoundError`: If the specified bundle does not exist
- `BundleExtractionError`: If the bundle could not be extracted
- `StorageError`: If there is insufficient disk space

## Kubectl Commands

These tools allow execution of kubectl commands against the initialized support bundle.

### kubectl

Executes a kubectl command against the initialized bundle.

**Request:**
```json
{
  "name": "kubectl",
  "input": {
    "command": "get pods -n kube-system",
    "timeout": 30,
    "json_output": true
  }
}
```

**Response (JSON output):**
```json
{
  "content": [
    {
      "type": "text",
      "text": "kubectl command executed successfully:\n```json\n{\n  \"apiVersion\": \"v1\",\n  \"items\": [\n    {\n      \"apiVersion\": \"v1\",\n      \"kind\": \"Pod\",\n      \"metadata\": {\n        \"name\": \"coredns-558bd4d5db-abcde\",\n        \"namespace\": \"kube-system\"\n      },\n      \"spec\": {\n        \"containers\": [\n          {\n            \"name\": \"coredns\",\n            \"image\": \"k8s.gcr.io/coredns:1.8.0\"\n          }\n        ]\n      },\n      \"status\": {\n        \"phase\": \"Running\"\n      }\n    }\n  ],\n  \"kind\": \"List\"\n}\n```\n\nCommand metadata:\n```json\n{\n  \"command\": \"kubectl get pods -n kube-system -o json\",\n  \"exit_code\": 0,\n  \"duration_ms\": 123\n}\n```"
    }
  ]
}
```

**Response (text output):**
```json
{
  "content": [
    {
      "type": "text",
      "text": "kubectl command executed successfully:\n```\nNAME                                     READY   STATUS    RESTARTS   AGE\ncoredns-558bd4d5db-abcde                 1/1     Running   0          5d\nkube-apiserver-master1                   1/1     Running   0          5d\nkube-controller-manager-master1          1/1     Running   0          5d\nkube-proxy-abcde                         1/1     Running   0          5d\nkube-scheduler-master1                   1/1     Running   0          5d\n```\n\nCommand metadata:\n```json\n{\n  \"command\": \"kubectl get pods -n kube-system\",\n  \"exit_code\": 0,\n  \"duration_ms\": 123\n}\n```"
    }
  ]
}
```

**Errors:**
- `NoBundleInitializedError`: If no bundle has been initialized yet
- `KubectlError`: If the kubectl command fails or is invalid
- `CommandNotSupportedError`: If the command is not supported in the bundle context

## File Operations

These tools enable exploration and analysis of files within the support bundle.

### list_files

Lists the contents of a directory in the bundle.

**Request:**
```json
{
  "name": "list_files",
  "input": {
    "path": "/kubernetes/pods",
    "recursive": false
  }
}
```

**Response:**
```json
{
  "content": [
    {
      "type": "text",
      "text": "Listed files in /kubernetes/pods non-recursively:\n```json\n[\n  {\n    \"name\": \"kube-system\",\n    \"path\": \"/kubernetes/pods/kube-system\",\n    \"type\": \"directory\",\n    \"size\": null,\n    \"modified\": \"2025-04-10T15:30:00Z\",\n    \"accessed\": \"2025-04-11T12:45:30Z\",\n    \"is_binary\": false\n  },\n  {\n    \"name\": \"default\",\n    \"path\": \"/kubernetes/pods/default\",\n    \"type\": \"directory\",\n    \"size\": null,\n    \"modified\": \"2025-04-10T15:30:00Z\",\n    \"accessed\": \"2025-04-11T12:45:30Z\",\n    \"is_binary\": false\n  },\n  {\n    \"name\": \"kube-apiserver-master1.yaml\",\n    \"path\": \"/kubernetes/pods/kube-apiserver-master1.yaml\",\n    \"type\": \"file\",\n    \"size\": 2456,\n    \"modified\": \"2025-04-10T15:30:00Z\",\n    \"accessed\": \"2025-04-11T12:45:30Z\",\n    \"is_binary\": false\n  }\n]\n```\n\nDirectory metadata:\n```json\n{\n  \"path\": \"/kubernetes/pods\",\n  \"recursive\": false,\n  \"total_files\": 1,\n  \"total_dirs\": 2\n}\n```"
    }
  ]
}
```

**Errors:**
- `NoBundleInitializedError`: If no bundle has been initialized yet
- `PathNotFoundError`: If the specified path does not exist
- `NotADirectoryError`: If the path is not a directory
- `SecurityError`: If the path is outside the bundle or otherwise restricted

### read_file

Reads the contents of a file in the bundle.

**Request:**
```json
{
  "name": "read_file",
  "input": {
    "path": "/kubernetes/pods/kube-system/coredns-558bd4d5db-abcde.yaml",
    "start_line": 0,
    "end_line": null
  }
}
```

**Response:**
```json
{
  "content": [
    {
      "type": "text",
      "text": "Read text file /kubernetes/pods/kube-system/coredns-558bd4d5db-abcde.yaml (lines 1-17 of 17):\n```\n   1 | apiVersion: v1\n   2 | kind: Pod\n   3 | metadata:\n   4 |   name: coredns-558bd4d5db-abcde\n   5 |   namespace: kube-system\n   6 | spec:\n   7 |   containers:\n   8 |   - name: coredns\n   9 |     image: k8s.gcr.io/coredns:1.8.0\n  10 |     ports:\n  11 |     - containerPort: 53\n  12 |       name: dns\n  13 |       protocol: UDP\n  14 |     - containerPort: 53\n  15 |       name: dns-tcp\n  16 |       protocol: TCP\n  17 | status:\n```"
    }
  ]
}
```

**Errors:**
- `NoBundleInitializedError`: If no bundle has been initialized yet
- `FileNotFoundError`: If the specified file does not exist
- `NotAFileError`: If the path is not a file
- `SecurityError`: If the path is outside the bundle or otherwise restricted

### grep_files

Searches for files containing a specific pattern.

**Request:**
```json
{
  "name": "grep_files",
  "input": {
    "pattern": "OOMKilled",
    "path": "/kubernetes/logs",
    "recursive": true,
    "glob_pattern": "*.log",
    "case_sensitive": false,
    "max_results": 1000
  }
}
```

**Response:**
```json
{
  "content": [
    {
      "type": "text",
      "text": "Found 3 matches for case-insensitive pattern 'OOMKilled' in /kubernetes/logs (matching *.log):\n\n**File: /kubernetes/logs/kube-system/mysql-backup-78945d95b-abcde.log**\n```\n  15 | Container was OOMKilled due to memory pressure\n```\n\n**File: /kubernetes/logs/monitoring/prometheus-server-558874d9c-fghij.log**\n```\n 278 | Previous container was OOMKilled, restarting with increased memory limits\n```\n\n**File: /kubernetes/events.log**\n```\n  42 | Pod monitoring/grafana-6584c8d677-abcde was evicted due to OOMKilled\n```\n\nSearch metadata:\n```json\n{\n  \"pattern\": \"OOMKilled\",\n  \"path\": \"/kubernetes/logs\",\n  \"glob_pattern\": \"*.log\",\n  \"total_matches\": 3,\n  \"files_searched\": 32,\n  \"recursive\": true,\n  \"case_sensitive\": false,\n  \"truncated\": false\n}\n```"
    }
  ]
}
```

**Errors:**
- `NoBundleInitializedError`: If no bundle has been initialized yet
- `PathNotFoundError`: If the specified path does not exist
- `InvalidPatternError`: If the search pattern is invalid
- `SecurityError`: If the path is outside the bundle or otherwise restricted

## Error Handling

The MCP Server uses a structured approach to error handling. This section documents the common error types and their meanings.

### Common Error Types

#### Authentication Errors

- `AuthenticationError`: Generic authentication failure
  - Example: "Authentication failed: Invalid or missing token"

#### Bundle Errors

- `BundleNotFoundError`: The specified bundle does not exist
  - Example: "Bundle with ID 'bundle-123' not found"
- `BundleExtractionError`: Failed to extract the bundle
  - Example: "Failed to extract bundle: Corrupted archive"
- `NoBundleInitializedError`: No bundle has been initialized
  - Example: "No bundle initialized. Use bundle__initialize first"

#### File Operation Errors

- `FileNotFoundError`: The specified file does not exist
  - Example: "File '/kubernetes/pods/missing.yaml' not found"
- `NotAFileError`: The specified path is not a file
  - Example: "Path '/kubernetes/pods' is a directory, not a file"
- `NotADirectoryError`: The specified path is not a directory
  - Example: "Path '/kubernetes/pods/pod.yaml' is a file, not a directory"
- `SecurityError`: Security violation in file access
  - Example: "Access to path outside bundle root is not allowed"

#### Kubectl Errors

- `KubectlError`: Error executing kubectl command
  - Example: "Kubectl command failed: Error from server: pod 'non-existent' not found"
- `CommandNotSupportedError`: The kubectl command is not supported
  - Example: "Command 'kubectl exec' is not supported in bundle context"

#### System Errors

- `StorageError`: Issues with storage
  - Example: "Insufficient disk space for bundle extraction"
- `ApiError`: Error communicating with external API
  - Example: "Failed to connect to support bundle service API"

### Error Response Structure

All errors are returned in a consistent format:

```json
{
  "error": {
    "type": "ErrorType",
    "message": "Detailed error message",
    "details": {
      "additional": "information",
      "about": "the error"
    }
  }
}
```

The `details` field is optional and may contain additional context about the error depending on the error type.