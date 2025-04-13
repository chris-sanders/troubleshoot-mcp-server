# Example Prompts and Responses

This document provides example prompts and responses for AI models interacting with the MCP Server for Kubernetes Support Bundles. These examples demonstrate how to effectively use the available tools to investigate and diagnose issues within a Kubernetes cluster using support bundles.

## Table of Contents

- [Basic Bundle Exploration](#basic-bundle-exploration)
- [Pod Troubleshooting Workflow](#pod-troubleshooting-workflow)
- [Node Analysis](#node-analysis)
- [Resource Utilization Review](#resource-utilization-review)
- [Network Connectivity Issues](#network-connectivity-issues)
- [Storage Problems](#storage-problems)
- [Control Plane Analysis](#control-plane-analysis)

## Basic Bundle Exploration

### Example 1: Initial Bundle Exploration

**User Prompt:**
```
I've just received a support bundle from my Kubernetes cluster. Can you help me explore what's in it?
```

**AI Response:**
```
I'll help you explore the support bundle. Let me first initialize it and check what's available.

Let me list the top-level directories to understand what information we have:

The bundle contains the following main directories:
- /kubernetes - Contains Kubernetes resource definitions and configurations
- /cluster-resources - Contains information about cluster-wide resources
- /logs - Contains log files from various components
- /system - Contains system information and metrics

Would you like me to:
1. Check the cluster's overall health?
2. Look for any error messages in logs?
3. Examine specific components like pods or nodes?
4. Check resource usage across the cluster?
```

### Example 2: Understanding Bundle Structure

**User Prompt:**
```
What kind of information is available in this support bundle? What are the main sections?
```

**AI Response:**
```
Let me explore the structure of this support bundle to understand the available information.

The support bundle contains the following main sections:

1. Kubernetes Resources (/kubernetes):
   - Pods, deployments, services, and other K8s resources
   - Configuration maps and secrets
   - RBAC configurations
   - Custom resources

2. Cluster Information (/cluster-resources):
   - Node status and information
   - Cluster version and components
   - API server information
   - Scheduler and controller manager information

3. Logs (/logs):
   - Container logs
   - Kubernetes component logs
   - System logs
   - Event logs

4. System Information (/system):
   - Operating system details
   - Kernel information
   - System resource usage
   - Network configuration

5. Troubleshooting Data:
   - Diagnostic outputs
   - Check results
   - Health assessment information

Is there a specific area you'd like to examine first?
```

## Pod Troubleshooting Workflow

### Example 3: Investigating a Crashing Pod

**User Prompt:**
```
One of our pods called "backend-api" in the "production" namespace keeps crashing. Can you help me figure out why?
```

**AI Response:**
```
I'll help you investigate why the "backend-api" pod in the "production" namespace is crashing. Let me check several things in sequence.

First, let me check the pod status:
The pod "backend-api" in the "production" namespace is in a CrashLoopBackOff state with 7 restarts.

Next, let me look at the pod events:
Events show the container is terminating with exit code 1, which typically indicates an error in the application.

Let me check the pod logs:
The logs show these error messages:
- "Error connecting to database at postgres-svc:5432"
- "Connection refused"
- "Application failed to start due to database connection error"

Now let me check if the database service exists and is running properly:
The "postgres-svc" service exists, but the associated postgres pod is in a Pending state.

Checking the postgres pod events:
Events show the postgres pod can't be scheduled due to insufficient memory resources.

Based on my investigation, here's what's happening:
1. Your backend-api pod is crashing because it can't connect to the database
2. The database pod (postgres) is not running
3. The postgres pod can't be scheduled because the nodes don't have enough memory resources

Recommendations:
1. Check node resource usage and consider adding more nodes or increasing memory
2. Temporarily reduce postgres memory requests to allow it to schedule
3. Consider adding connection retry logic to the backend-api to handle temporary database unavailability
```

### Example 4: Analyzing Application Logs

**User Prompt:**
```
Our application in the frontend pods is showing errors in the browser. Can you check the logs to see what might be causing it?
```

**AI Response:**
```
I'll check the logs for your frontend pods to identify what might be causing the errors shown in the browser.

First, let me locate the frontend pods:
Found 3 frontend pods in the "default" namespace: frontend-6d4b9f4f7-1abc, frontend-6d4b9f4f7-2def, frontend-6d4b9f4f7-3ghi

Let me examine the logs for these pods:

From pod frontend-6d4b9f4f7-1abc logs:
- Multiple 404 errors when trying to fetch from "/api/users"
- Console errors: "Failed to load resource: net::ERR_CONNECTION_REFUSED"
- Several React component errors: "Cannot read property 'data' of undefined"

Let me check the backend API service:
The "api-service" appears to exist but is selecting pods with label "app=backend-api"

Checking the backend-api pods:
There are 0 pods matching the selector "app=backend-api" - this is the issue!

Looking at events for the backend deployment:
The backend deployment failed to create pods due to an error pulling the container image "mycompany/backend-api:latest" - the image cannot be found.

Here's what's happening:
1. Your frontend is trying to communicate with a backend API service
2. The backend pods don't exist because they couldn't be created
3. The image pull is failing which is preventing the backend pods from starting
4. This causes the frontend to receive connection errors when trying to reach the API

Recommendations:
1. Check the image name and tag for the backend service
2. Ensure the image exists in your registry
3. Verify authentication to your container registry
4. Consider specifying a specific version instead of 'latest'
```

## Node Analysis

### Example 5: Investigating Node Problems

**User Prompt:**
```
Our node "worker-node-03" is showing as NotReady. What could be wrong with it?
```

**AI Response:**
```
I'll investigate why worker-node-03 is in a NotReady state by examining several aspects of the node and related components.

First, let me check the node status details:
Node worker-node-03 is marked as NotReady with the following conditions:
- NetworkUnavailable: False
- MemoryPressure: False 
- DiskPressure: True
- PIDPressure: False
- Ready: False
Last heartbeat was 15 minutes ago.

The DiskPressure condition is True, which indicates disk space issues.

Let me check the kubelet logs on this node:
Found in kubelet logs:
- "Eviction manager: node has disk pressure" 
- "Failed to garbage collect required amount of images"
- "Node condition status changed: DiskPressure=True"

Looking at disk usage metrics for this node:
- Root filesystem usage: 94% (14.1GB/15GB)
- Image filesystem usage: 89% (8.9GB/10GB)

Examining pods on this node:
Several pods have large persistent volume claims and/or large log files. One pod "log-collector" has a 3GB log file.

The issue is clear: worker-node-03 is experiencing disk pressure (running out of disk space) which has triggered the node to be marked as NotReady.

Recommendations:
1. Clean up large container images not in use: 'crictl rmi --prune'
2. Rotate and compress large log files
3. Check the log-collector pod which has a very large log file
4. Consider increasing disk space allocation for the node
5. Implement log rotation if not already configured
```

### Example 6: Resource Utilization Analysis

**User Prompt:**
```
I suspect we might have a resource issue on our nodes. Can you analyze resource utilization across our cluster?
```

**AI Response:**
```
I'll analyze resource utilization across your cluster to identify any potential issues.

Let me check overall node resource usage:

Node Resource Summary:
1. master-1:
   - CPU: 82% used (3.3/4 cores)
   - Memory: 76% used (12.2/16 GB)
   - Disk: 45% used

2. worker-1:
   - CPU: 91% used (7.3/8 cores)
   - Memory: 94% used (15.1/16 GB)
   - Disk: 52% used

3. worker-2:
   - CPU: 87% used (7.0/8 cores)
   - Memory: 89% used (14.2/16 GB)
   - Disk: 48% used

4. worker-3:
   - CPU: 65% used (5.2/8 cores)
   - Memory: 97% used (15.5/16 GB)
   - Disk: 73% used

Let me look at pods with high resource usage:
1. elasticsearch-master-0:
   - CPU: 2.1 cores
   - Memory: 7.2 GB
   
2. prometheus-server-7bc4b8f9-2abc:
   - CPU: 1.8 cores
   - Memory: 4.3 GB

3. mongodb-primary-0:
   - CPU: 1.3 cores
   - Memory: 3.8 GB

Let me check for resource-related events:
Found 14 recent OOMKilled events across the cluster
Found 23 events related to CPU throttling

Based on my analysis:
1. Your cluster is experiencing significant resource pressure
2. Workers 1, 2, and 3 are all near memory capacity (>89% used)
3. Worker-1 has critical CPU utilization at 91%
4. Several pods have been OOMKilled due to memory constraints
5. Multiple pods are experiencing CPU throttling

Recommendations:
1. Consider adding more nodes to distribute workload
2. Increase memory allocation for existing nodes, especially worker-3
3. Review resource requests/limits for elasticsearch and prometheus
4. Implement pod autoscaling for applications with variable workloads
5. Consider dedicated nodes for resource-intensive services like elasticsearch
```

## Network Connectivity Issues

### Example 7: Diagnosing Service Connectivity Problems

**User Prompt:**
```
Our frontend service can't seem to connect to the backend service. The frontend service is in the "web" namespace and the backend service is in the "api" namespace. Can you help troubleshoot?
```

**AI Response:**
```
I'll help troubleshoot the connectivity issue between your frontend service in the "web" namespace and backend service in the "api" namespace.

Let me first verify both services exist and check their configurations:

Frontend service in "web" namespace:
- Service name: frontend-svc
- Type: ClusterIP
- IP: 10.100.14.18
- Selector: app=frontend
- Ports: 80/TCP -> 8080/TCP

Backend service in "api" namespace:
- Service name: backend-svc
- Type: ClusterIP
- IP: 10.100.22.45
- Selector: app=backend
- Ports: 80/TCP -> 8000/TCP

Checking if frontend pods exist and match the service selector:
Yes, found 2 running pods with label app=frontend in the web namespace.

Checking if backend pods exist and match the service selector:
Yes, found 1 running pod with label app=backend in the api namespace.

Let me check the NetworkPolicy resources:
Found a NetworkPolicy in the "api" namespace that restricts ingress to the backend pods.
The policy only allows connections from pods with label "role=api-client" in any namespace.

Checking the frontend pods' labels:
Frontend pods have labels app=frontend but do not have the required role=api-client label.

Looking at frontend pod logs:
Logs show connection timeouts when trying to reach backend-svc.api.svc.cluster.local

The issue is identified: There's a NetworkPolicy in the "api" namespace that's blocking connections from your frontend pods to the backend service because the frontend pods don't have the required label "role=api-client".

Recommendations:
1. Add the label "role=api-client" to your frontend deployment:
   kubectl -n web label deployment frontend role=api-client

2. Or modify the NetworkPolicy in the "api" namespace to allow connections from the frontend pods.

3. Consider namespace-level network policies that allow services in the "web" namespace to access services in the "api" namespace.

4. Also verify the correct service DNS name is being used: backend-svc.api.svc.cluster.local
```

### Example 8: External Connectivity Issues

**User Prompt:**
```
Our application running in the cluster can't connect to external services. We have a pod called "external-caller" in the "demo" namespace that needs to reach api.example.com. Can you investigate?
```

**AI Response:**
```
I'll investigate why your "external-caller" pod in the "demo" namespace can't connect to api.example.com.

First, let me check the pod status and details:
Pod "external-caller" is Running with 1/1 containers ready.

Let me examine the pod logs:
Logs show connection timeout errors when trying to connect to api.example.com:
- "Failed to connect to api.example.com: Connection timed out"
- "DNS resolution successful, but connection failed"

Now I'll check cluster networking components:

Checking CoreDNS configuration and logs:
CoreDNS appears to be functioning correctly. It's resolving api.example.com to 203.0.113.42.

Checking for network policies that might restrict egress:
Found a cluster-wide NetworkPolicy that restricts egress to specific CIDRs.
The policy allows egress only to 10.0.0.0/8, 172.16.0.0/12, and 192.168.0.0/16.
The address 203.0.113.42 for api.example.com is not in these allowed ranges.

Checking if any SNAT or egress gateway is configured:
There's no dedicated egress gateway. Nodes use direct outbound traffic.

Let me check node network configuration:
Node network configuration looks normal, but I notice that outbound traffic to non-RFC1918 addresses requires proxy configuration.

Looking at pod spec:
The pod doesn't have any proxy environment variables set.

I've identified the issue: There's a restrictive egress NetworkPolicy blocking connections to non-RFC1918 IP ranges, which includes api.example.com (203.0.113.42).

Recommendations:
1. Update the NetworkPolicy to allow egress to 203.0.113.42/32 (or a wider range if needed)
2. Or add a label to the "external-caller" pod that exempts it from this policy
3. Consider implementing an egress gateway or proxy for better control of external traffic
4. Set up proper monitoring for external connectivity issues
```

## Resource Utilization Review

### Example 9: High Memory Usage Analysis

**User Prompt:**
```
Our cluster seems to be running out of memory frequently. Can you analyze memory usage patterns and identify the most memory-intensive workloads?
```

**AI Response:**
```
I'll analyze memory usage patterns in your cluster to identify the most memory-intensive workloads and potential issues.

Let me first check node-level memory metrics:

Nodes Memory Usage:
1. node-1: 92% used (14.7/16 GB)
2. node-2: 88% used (28.2/32 GB)
3. node-3: 95% used (15.2/16 GB)
4. node-4: 79% used (25.3/32 GB)

Now, let me identify the top memory-consuming pods:

Top Memory Consumers:
1. elasticsearch-master-0 (logging): 7.6 GB
2. mongo-0 (database): 5.3 GB
3. redis-master-0 (cache): 4.2 GB
4. kafka-0 (messaging): 3.8 GB
5. prometheus-server-5bc87f9d87-ab12 (monitoring): 3.5 GB

Looking at memory-related events in the last 24 hours:
- 12 OOMKilled events across the cluster
- 8 eviction warnings due to memory pressure
- 3 pod rescheduling events due to node memory pressure

Checking pods with potential memory leaks:
The application pod "backend-api-6f7bd9c874-xyz1" shows steadily increasing memory usage over time, growing from 400MB to 2.3GB over 3 days without corresponding traffic increases.

Analyzing memory request vs. limits configuration:
Several pods have memory limits set but no requests, which can lead to poor scheduling decisions:
- web-frontend (limit: 1GB, request: not set)
- api-gateway (limit: 2GB, request: not set)

Based on my analysis:

1. Major memory consumers are data-related services (elasticsearch, mongo, redis, kafka)
2. Node-3 is critically high on memory usage at 95%
3. There's a potential memory leak in the backend-api application
4. Some pods have improper memory request/limit configurations
5. OOMKilled events are occurring regularly, indicating memory shortage

Recommendations:

1. Increase cluster memory capacity, especially for node-1 and node-3
2. Investigate the backend-api application for memory leaks
3. Set appropriate memory requests for all pods to improve scheduler decisions
4. Consider moving elasticsearch to dedicated nodes with more memory
5. Implement vertical pod autoscaling for workloads with variable memory needs
6. Enable memory overcommit management at the cluster level
7. Monitor GC patterns in Java applications (elasticsearch, kafka) to optimize heap settings
```

### Example 10: CPU Throttling Investigation

**User Prompt:**
```
Our application performance seems slow, and I suspect CPU throttling might be happening. Can you check if any pods are being throttled due to CPU limits?
```

**AI Response:**
```
I'll investigate if any pods in your cluster are experiencing CPU throttling due to CPU limits, which could be affecting your application performance.

Let me first check for CPU throttling metrics and events:

CPU Throttling Events (last 24 hours):
- Found 143 throttling events across the cluster
- Most affected namespaces: production (87 events), processing (32 events), batch (24 events)

Now, let me identify the most throttled pods:

Top CPU-Throttled Pods:
1. worker-processing-5d78c9f57-abc1 (production):
   - Throttled: 76% of the time
   - CPU Limit: 1 core
   - CPU Usage: averaging 0.95 cores (95% of limit)
   
2. api-server-7c84bd9fd6-def2 (production):
   - Throttled: 58% of the time
   - CPU Limit: 0.5 cores
   - CPU Usage: spiking to 0.8 cores during peak times
   
3. batch-job-processor-67d5c789f-ghi3 (batch):
   - Throttled: 45% of the time
   - CPU Limit: 2 cores
   - CPU Usage: averaging 1.7 cores with spikes to 3.8 cores

4. data-etl-6f98d4c5b7-jkl4 (processing):
   - Throttled: 42% of the time
   - CPU Limit: 1.5 cores
   - CPU Usage: varies widely from 0.3 to 4.2 cores

Checking CPU request vs. limit configurations:
Several pods have very tight CPU limits compared to their requests:
- worker-processing: request 0.9, limit 1.0 (10% headroom)
- api-server: request 0.5, limit 0.5 (0% headroom)
- data-etl: request 1.0, limit 1.5 (50% headroom)

Analyzing node CPU allocation:
- The cluster has high CPU allocation (requested CPU vs. available)
- Node-1: 92% CPU allocated
- Node-2: 87% CPU allocated
- Node-3: 94% CPU allocated

Based on my analysis:

1. Significant CPU throttling is occurring, particularly in the production namespace
2. The worker-processing and api-server pods are the most severely throttled
3. Several pods have insufficient headroom between CPU requests and limits
4. Some workloads (like data-etl) have highly variable CPU needs that exceed their limits
5. The cluster has high overall CPU allocation, reducing flexibility

Recommendations:

1. Increase CPU limits for the most throttled pods, particularly:
   - api-server: increase from 0.5 to at least 1.0 cores
   - worker-processing: increase from 1.0 to at least 1.5 cores

2. For workloads with variable CPU requirements (like data-etl):
   - Consider using Horizontal Pod Autoscaling instead of relying on high CPU limits
   - Or remove CPU limits entirely if the workload is critical and won't affect other applications

3. Add more nodes to the cluster to reduce overall CPU allocation pressure

4. Review application code in api-server, which shows consistent throttling, for potential optimization opportunities

5. For batch jobs, consider setting appropriate QoS class to ensure they don't interfere with production workloads
```

## Control Plane Analysis

### Example 11: API Server Performance Issues

**User Prompt:**
```
Kubectl commands are taking a long time to respond, and sometimes time out completely. I think there might be an issue with the Kubernetes API server. Can you investigate?
```

**AI Response:**
```
I'll investigate the performance issues with your Kubernetes API server that are causing slow kubectl commands and timeouts.

First, let me check the API server logs:

From the kube-apiserver logs:
- Numerous log entries showing "request took too long" warnings
- Several "etcd request took too long" messages
- High latency metrics for LIST and WATCH operations
- Multiple "415 goroutines currently running" messages indicating high load

Let me analyze API server metrics:
- Request rate: averaging 245 requests/second (high load)
- P99 latency: 8.2 seconds for LIST operations
- P99 latency: 12.3 seconds for WATCH operations
- Request timeouts: 37 in the last hour
- Most expensive request types: LIST pods across all namespaces, WATCH nodes

Now checking etcd performance:
- etcd disk IOPS: near saturation (92% of capacity)
- etcd disk latency: averaging 15ms (high)
- etcd leader changes: 3 in the last 24 hours (potential instability)

Looking at API server resources:
- CPU usage: 3.7 cores (92% of limit)
- Memory usage: 5.2GB (87% of limit)
- High rate of garbage collection

Examining client requests:
- Several service accounts making frequent LIST requests across all namespaces
- A monitoring system making unbounded watch requests
- Multiple instances of kubectl commands with no resource limits specified

Based on my analysis:

1. Your API server is experiencing overload from too many expensive requests
2. The etcd database is showing signs of performance issues (high disk latency)
3. API server resources (CPU and memory) are nearly exhausted
4. Several clients are making inefficient API requests

Recommendations:

1. Optimize client requests:
   - Add namespace filters to LIST and WATCH operations
   - Add field selectors and label selectors to limit result sizes
   - Use resource versions for watch operations to reduce load

2. Increase API server resources:
   - Scale up CPU allocation to at least 4-6 cores
   - Increase memory allocation to 8GB
   - Consider adding another API server replica

3. Optimize etcd:
   - Move etcd to SSD storage if not already using it
   - Ensure etcd has dedicated resources
   - Confirm proper etcd defragmentation schedule

4. Add rate limiting:
   - Configure API priority and fairness settings
   - Set appropriate max inflight requests
   - Consider implementing client-side rate limiting for heavy users

5. Review monitoring systems that may be overloading the API server with watch requests
```

### Example 12: ETCD Backup Verification

**User Prompt:**
```
We need to make sure our etcd backups are working properly. Can you check the status of etcd backups in our cluster?
```

**AI Response:**
```
I'll investigate the status of etcd backups in your cluster to ensure they're working properly.

First, let me check for any backup-related configurations and jobs:

Looking for etcd backup configurations:
Found a CronJob "etcd-backup" in the "kube-system" namespace scheduled to run daily at 2 AM.

Checking the execution history of the etcd-backup job:
- Last successful run: 2 days ago
- Recent failures: 3 consecutive failures in the last 3 days
- Error message from last run: "failed to connect to etcd endpoint"

Examining the etcd backup pod logs:
The logs indicate an authentication issue with etcd. The backup process is failing to authenticate with the etcd cluster using the provided certificates.

Let me check the backup storage configuration:
- Backup destination: AWS S3 bucket "k8s-etcd-backups"
- Recent backup size: 24 MB (from successful backup 2 days ago)
- Last successful backup file: "etcd-snapshot-2025-04-09-020012.db"

Checking the etcd backup script:
The backup script is using expired certificates. The client certificate expired 3 days ago.

Verifying backup completeness:
The last successful backup appears to contain a complete etcd snapshot based on its size and the verification logs.

Based on my analysis:

1. Your etcd backups were working until 3 days ago
2. Backups are now failing due to expired TLS certificates
3. The backup storage configuration (S3 bucket) appears correct
4. The last successful backup is 2 days old, which exceeds recommended backup frequency

Recommendations:

1. Immediately renew the etcd client certificates used by the backup process:
   - Update the secrets in the "kube-system" namespace
   - The specific secret is "etcd-backup-certs"

2. After certificate renewal, trigger a manual backup to verify it works:
   - kubectl create job --from=cronjob/etcd-backup -n kube-system etcd-backup-manual

3. Implement backup validation:
   - Add a step to verify backup integrity after creation
   - Consider restoring to a test environment periodically

4. Enhance monitoring:
   - Add alerts for backup failures
   - Monitor certificate expiration dates
   - Track backup size trends to detect potential issues

5. Consider increasing backup frequency to at least once per day for critical clusters

6. Implement proper certificate rotation automation to prevent future expirations
```

## Storage Problems

### Example 13: Persistent Volume Issues

**User Prompt:**
```
We're having issues with persistent volumes. Some pods can't access their storage, and others have stuck volumes. Can you investigate what's happening?
```

**AI Response:**
```
I'll investigate your persistent volume issues to determine why some pods can't access their storage and why some volumes are stuck.

First, let me check the overall status of PVs and PVCs:

Persistent Volume Status:
- Total PVs: 28
- Available: 4
- Bound: 19
- Released: 2
- Failed: 3

Persistent Volume Claims Status:
- Total PVCs: 23
- Bound: 19
- Pending: 4

Now, let me look at the problematic PVs in detail:

Failed PVs:
1. pv-data-mysql-0:
   - Status: Failed
   - Reason: "ProvisioningFailed"
   - Message: "failed to provision volume: timed out waiting for the condition"
   - Storage Class: "standard-ssd"

2. pv-logs-elk-1:
   - Status: Failed  
   - Reason: "ProvisioningFailed"
   - Message: "failed to provision volume with StorageClass 'standard-ssd': rpc error: code = ResourceExhausted"

Examining storage classes:
The "standard-ssd" storage class uses a provisioner that appears to be reaching capacity limits.

Checking pods with mount issues:
1. mysql-0 (database namespace):
   - Pod status: ContainerCreating
   - Events: "Unable to mount volumes: timeout waiting for volume"
   - PVC: mysql-data-mysql-0 (Pending)

2. elasticsearch-data-2 (logging namespace):
   - Pod status: Running but with readiness probe failures
   - Events: "Volume not attached correctly" 
   - PVC: elasticsearch-data-elasticsearch-data-2 (Bound)

Looking at storage provider metrics:
- Storage capacity utilization: 92%
- Storage provisioning latency: Very high (32s avg)
- Failed storage operations: 14 in last hour

Checking Released but not Available volumes:
- Two volumes are in Released state but not being reclaimed
- One is from a StatefulSet pod that was deleted
- The reclaim policy is "Retain" which prevents automatic cleanup

Based on my analysis:

1. Your storage system is approaching capacity limits (92% utilized)
2. The storage provisioner for "standard-ssd" is failing to create new volumes
3. Some pods can't start because their PVCs are stuck in Pending state
4. Released volumes aren't being reclaimed due to the "Retain" policy
5. Some attached volumes have connectivity issues

Recommendations:

1. Address storage capacity issues:
   - Increase capacity in your storage provider
   - Clean up unused PVs with "Retain" policy that are no longer needed

2. For stuck volumes:
   - Check the storage provider's health and connectivity
   - For volumes in "Released" state that should be reused, manually change their status or delete and recreate them

3. For pods that can't mount volumes:
   - Ensure the node has connectivity to the storage provider
   - Check if the node has reached its attached volume limit

4. Fix storage class configuration:
   - Review QoS settings in your storage class
   - Consider creating a new storage class that uses a different storage pool

5. Implement better monitoring:
   - Add alerts for storage capacity thresholds
   - Monitor volume attachment latency
   - Set up alerts for PVCs stuck in Pending state
```

## Network Connectivity Issues

### Example 14: DNS Resolution Problems

**User Prompt:**
```
Our pods are having trouble resolving DNS names. Some services can't be reached by their service names. Can you help diagnose the DNS issues?
```

**AI Response:**
```
I'll help diagnose the DNS resolution issues preventing your pods from reaching services by their service names.

First, let me check the CoreDNS deployment and configuration:

CoreDNS Status:
- Deployment: 2 replicas, both Running
- Pod status: Both pods are Running and Ready
- CPU usage: 23% (moderate)
- Memory usage: 68% (moderate-high)

Examining CoreDNS configuration (ConfigMap coredns in kube-system):
The Corefile configuration looks standard, with expected plugins including kubernetes, forward, and cache.

Checking CoreDNS logs:
- Found multiple error entries: "NXDOMAIN: kubernetes.default.svc.cluster.local."
- Several timeout messages when forwarding external queries
- Multiple cache expiration warnings
- Some pods getting "SERVFAIL" responses

Let me check CoreDNS service configuration:
- Service IP: 10.96.0.10
- Port: 53 UDP/TCP
- Endpoints: Match the CoreDNS pod IPs

Examining pod DNS configurations:
- Most pods use the default DNS config from the cluster
- Some pods have custom dnsConfig that might be conflicting
- Found 3 pods with incorrect dnsPolicy set to "None" without custom config

Checking network policies that might affect DNS:
Found a network policy in the "app" namespace that restricts egress but doesn't explicitly allow DNS traffic on port 53.

Checking node DNS resolution:
All nodes can resolve external and internal DNS names correctly.

Looking at DNS metrics:
- Query latency: High (120ms average)
- Cache hit rate: Low (45%)
- Error rate: 12% of queries failing
- Query volume: Very high (500 queries/second)

Based on my analysis:

1. CoreDNS is running but experiencing performance issues due to high query volume
2. Some pods have misconfigured DNS settings
3. Network policies are blocking DNS traffic for pods in the "app" namespace
4. There are potential connectivity issues between pods and CoreDNS
5. CoreDNS cache performance is suboptimal

Recommendations:

1. Fix network policy configuration:
   - Add explicit rules to allow egress traffic to DNS service (10.96.0.10:53) for UDP and TCP
   - Example rule: allow egress to 10.96.0.10/32 port 53 protocol UDP/TCP

2. Correct pod DNS configurations:
   - Fix pods with dnsPolicy "None" that don't have custom configs
   - Standardize DNS configuration across deployments

3. Scale up CoreDNS:
   - Increase replicas from 2 to 3-4 based on your cluster size
   - Increase resource allocations, especially memory

4. Optimize CoreDNS configuration:
   - Increase cache TTL for improved performance
   - Add health plugin for better monitoring
   - Consider enabling autopath plugin for reduced query volume

5. Implement DNS monitoring:
   - Add latency and error rate monitoring
   - Set up alerts for DNS failures
   - Monitor cache hit rate

6. Check cluster network plugin configuration, as some CNI issues can affect pod-to-service communication
```

The examples in this document demonstrate various use cases and workflows for troubleshooting Kubernetes clusters using support bundles through the MCP Server. They show how AI models can effectively use the available tools to diagnose and address common issues.