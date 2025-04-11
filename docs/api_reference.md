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
  "content": "response content or object"
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

### bundle__list

Lists available support bundles.

**Request:**
```json
{
  "name": "bundle__list"
}
```

**Response:**
```json
{
  "content": [
    {
      "id": "bundle-123",
      "name": "cluster-1-bundle",
      "created_at": "2025-04-10T15:30:00Z",
      "size": "145MB"
    },
    {
      "id": "bundle-456",
      "name": "cluster-2-bundle",
      "created_at": "2025-04-11T12:15:00Z",
      "size": "180MB"
    }
  ]
}
```

**Errors:**
- `AuthenticationError`: If the SBCTL_TOKEN is invalid or missing
- `ApiError`: If the support bundle service is unavailable

### bundle__initialize

Initializes (downloads and extracts) a support bundle for use.

**Request:**
```json
{
  "name": "bundle__initialize",
  "input": {
    "bundle_id": "bundle-123"
  }
}
```

**Response:**
```json
{
  "content": {
    "path": "/path/to/extracted/bundle",
    "id": "bundle-123",
    "name": "cluster-1-bundle",
    "extracted_size": "450MB"
  }
}
```

**Errors:**
- `AuthenticationError`: If the SBCTL_TOKEN is invalid or missing
- `BundleNotFoundError`: If the specified bundle does not exist
- `BundleExtractionError`: If the bundle could not be extracted
- `StorageError`: If there is insufficient disk space

### bundle__info

Gets information about the currently initialized bundle.

**Request:**
```json
{
  "name": "bundle__info"
}
```

**Response:**
```json
{
  "content": {
    "id": "bundle-123",
    "name": "cluster-1-bundle",
    "path": "/path/to/extracted/bundle",
    "created_at": "2025-04-10T15:30:00Z",
    "kubernetes_version": "1.27.3",
    "node_count": 5,
    "resource_count": {
      "pods": 42,
      "deployments": 15,
      "services": 18
    }
  }
}
```

**Errors:**
- `NoBundleInitializedError`: If no bundle has been initialized yet

## Kubectl Commands

These tools allow execution of kubectl commands against the initialized support bundle.

### kubectl__execute

Executes a kubectl command against the initialized bundle.

**Request:**
```json
{
  "name": "kubectl__execute",
  "input": {
    "command": "get pods -n kube-system"
  }
}
```

**Response (text output):**
```json
{
  "content": "NAME                                     READY   STATUS    RESTARTS   AGE\ncoredns-558bd4d5db-abcde                 1/1     Running   0          5d\nkube-apiserver-master1                   1/1     Running   0          5d\nkube-controller-manager-master1          1/1     Running   0          5d\nkube-proxy-abcde                         1/1     Running   0          5d\nkube-scheduler-master1                   1/1     Running   0          5d"
}
```

**Response (JSON output):**
```json
{
  "content": {
    "apiVersion": "v1",
    "items": [
      {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
          "name": "coredns-558bd4d5db-abcde",
          "namespace": "kube-system"
        },
        "spec": {
          "containers": [
            {
              "name": "coredns",
              "image": "k8s.gcr.io/coredns:1.8.0"
            }
          ]
        },
        "status": {
          "phase": "Running"
        }
      }
    ],
    "kind": "List"
  }
}
```

**Errors:**
- `NoBundleInitializedError`: If no bundle has been initialized yet
- `KubectlError`: If the kubectl command fails or is invalid
- `CommandNotSupportedError`: If the command is not supported in the bundle context

## File Operations

These tools enable exploration and analysis of files within the support bundle.

### files__list_directory

Lists the contents of a directory in the bundle.

**Request:**
```json
{
  "name": "files__list_directory",
  "input": {
    "path": "/kubernetes/pods"
  }
}
```

**Response:**
```json
{
  "content": [
    {
      "name": "kube-system",
      "type": "directory",
      "size": null,
      "modified": "2025-04-10T15:30:00Z"
    },
    {
      "name": "default",
      "type": "directory",
      "size": null,
      "modified": "2025-04-10T15:30:00Z"
    },
    {
      "name": "kube-apiserver-master1.yaml",
      "type": "file",
      "size": 2456,
      "modified": "2025-04-10T15:30:00Z"
    }
  ]
}
```

**Errors:**
- `NoBundleInitializedError`: If no bundle has been initialized yet
- `PathNotFoundError`: If the specified path does not exist
- `NotADirectoryError`: If the path is not a directory
- `SecurityError`: If the path is outside the bundle or otherwise restricted

### files__read_file

Reads the contents of a file in the bundle.

**Request:**
```json
{
  "name": "files__read_file",
  "input": {
    "path": "/kubernetes/pods/kube-system/coredns-558bd4d5db-abcde.yaml"
  }
}
```

**Response:**
```json
{
  "content": "apiVersion: v1\nkind: Pod\nmetadata:\n  name: coredns-558bd4d5db-abcde\n  namespace: kube-system\nspec:\n  containers:\n  - name: coredns\n    image: k8s.gcr.io/coredns:1.8.0\n    ports:\n    - containerPort: 53\n      name: dns\n      protocol: UDP\n    - containerPort: 53\n      name: dns-tcp\n      protocol: TCP\n    resources:\n      limits:\n        memory: 170Mi\n      requests:\n        cpu: 100m\n        memory: 70Mi\nstatus:\n  phase: Running"
}
```

**Errors:**
- `NoBundleInitializedError`: If no bundle has been initialized yet
- `FileNotFoundError`: If the specified file does not exist
- `NotAFileError`: If the path is not a file
- `SecurityError`: If the path is outside the bundle or otherwise restricted

### files__search_files

Searches for files containing a specific pattern.

**Request:**
```json
{
  "name": "files__search_files",
  "input": {
    "pattern": "OOMKilled",
    "path": "/kubernetes/logs"
  }
}
```

**Response:**
```json
{
  "content": [
    "/kubernetes/logs/kube-system/mysql-backup-78945d95b-abcde.log:15: Container was OOMKilled due to memory pressure",
    "/kubernetes/logs/monitoring/prometheus-server-558874d9c-fghij.log:278: Previous container was OOMKilled, restarting with increased memory limits",
    "/kubernetes/events.log:42: Pod monitoring/grafana-6584c8d677-abcde was evicted due to OOMKilled"
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