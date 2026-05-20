---
title: "Self-Hosted Kubernetes Pod Debugging: kubectl-debug vs kubectl-trace vs Ephemeral Containers (2026)"
date: "2026-05-21"
tags: ["kubernetes", "debugging", "containers", "self-hosted"]
draft: false
---

Debugging running pods in Kubernetes is notoriously difficult. Containers are designed to be minimal — often without `curl`, `ping`, `strace`, or even `bash`. When a production pod is misbehaving, you need tools that can inspect the container's network, filesystem, and processes without disrupting the running application.

In this guide, we compare three approaches to self-hosted Kubernetes pod debugging: **kubectl-debug** for spawning debug sidecars, **kubectl-trace** for running BPF traces on pod workloads, and Kubernetes **native ephemeral containers** (a built-in feature since v1.23) for inline debugging sessions.

## Comparison Overview

| Feature | kubectl-debug | kubectl-trace | Ephemeral Containers |
|---------|--------------|---------------|---------------------|
| GitHub Stars | 2,306 | 2,178 | Built-in (K8s) |
| Last Updated | Oct 2023 | Mar 2023 | Ongoing (K8s core) |
| Debug Approach | Sidecar container | BPF/eBPF trace | Native ephemeral container |
| Requires CRD | Yes | Yes | No |
| Network Namespace Access | Yes (shared) | Yes (via eBPF) | Yes (targetContainer) |
| Process Namespace Access | Yes | Yes (via eBPF) | Yes (targetPIDNamespace) |
| Filesystem Access | Yes (mounted) | No | Yes (mounted) |
| System Call Tracing | Via installed tools | Via bpftrace | Via installed tools |
| Production Safety | Moderate (sidecar) | High (non-invasive) | High (native) |
| Kubernetes Version | 1.12+ | 1.12+ | 1.23+ (GA) |
| Docker Deployable | N/A (kubectl plugin) | N/A (kubectl plugin) | N/A (native feature) |

## kubectl-debug: Debug Sidecar Injection

**kubectl-debug** (github.com/aylei/kubectl-debug) is a kubectl plugin that spawns a temporary debug container sharing the target pod's network and PID namespaces. It provides a full-featured debugging environment — including common network diagnostic tools — inside the context of the problematic pod.

### Key Features

- **Namespace sharing**: The debug container shares the target pod's network, PID, and IPC namespaces — giving you the same network stack and process view.
- **Pre-built debug images**: Ships with images containing `curl`, `dig`, `tcpdump`, `strace`, `nslookup`, `netstat`, `ss`, and other diagnostic utilities.
- **Automatic cleanup**: The debug container is automatically removed when the debugging session ends.
- **Custom images**: You can specify any Docker image as the debug environment — useful for language-specific debugging tools.
- **Port-forwarding**: Built-in port-forwarding to access the pod's services from your local machine.

### Installation

```bash
# Install via krew
kubectl krew install debug

# Or download binary from GitHub releases
curl -Lo kubectl-debug https://github.com/aylei/kubectl-debug/releases/download/v0.1.1/kubectl-debug-linux-amd64
chmod +x kubectl-debug
sudo mv kubectl-debug /usr/local/bin/
```

### Usage Examples

```bash
# Debug a pod with the default debug image
kubectl debug my-pod -n production

# Use a custom debug image
kubectl debug my-pod --image=nicolaka/netshoot

# Share PID namespace to see all processes
kubectl debug my-pod --target-container=app --share-pid

# Run a specific command instead of interactive shell
kubectl debug my-pod --command -- tcpdump -i eth0 port 8080

# Debug a specific container in a multi-container pod
kubectl debug my-pod --container=web-server --image=busybox
```

### How It Works

kubectl-debug creates a new pod that shares the target pod's namespaces. It uses the Kubernetes API to create a sidecar-like container with the debug image, attaching to the same network namespace so you can use network diagnostic tools as if you were inside the original container.

### When to Use kubectl-debug

- **Network debugging**: Using `tcpdump`, `curl`, or `dig` to diagnose connectivity issues
- **Process inspection**: Using `ps`, `strace`, or `lsof` to understand application behavior
- **Filesystem access**: Inspecting mounted volumes, configmaps, or secrets
- **No cluster modifications needed**: Works as a kubectl plugin without requiring CRDs or operators

## kubectl-trace: BPF-Based Observability

**kubectl-trace** (github.com/iovisor/kubectl-trace) is a kubectl plugin that schedules bpftrace programs on Kubernetes nodes. Unlike kubectl-debug, it does not inject containers into pods — instead, it uses eBPF (extended Berkeley Packet Filter) to observe kernel-level behavior non-invasively.

### Key Features

- **eBPF-based tracing**: Uses bpftrace to attach probes to kernel functions, system calls, and tracepoints — all without modifying the target pod.
- **Non-invasive**: Does not require any changes to the target pod or container — zero runtime overhead on the application.
- **Pre-built trace programs**: Includes common trace scripts for HTTP latency, TCP retransmits, file I/O profiling, and memory allocation tracking.
- **Node-level scheduling**: Runs trace programs on specific nodes or across the entire cluster.
- **Output streaming**: Streams trace output back to your local terminal in real-time.

### Installation

```bash
# Install via krew
kubectl krew install trace

# Or install from source
go install github.com/iovisor/kubectl-trace@latest
```

### Usage Examples

```bash
# Trace all TCP retransmits on a node
kubectl trace run node-1 -e 'tracepoint:tcp:tcp_retransmit_skb { printf("retransmit from %s\n", str(args->sk->__sk_common.skc_daddr)); }'

# Trace HTTP request latency in a pod's network namespace
kubectl trace run pod/my-pod -e '
  kprobe:tcp_sendmsg {
    @start[tid] = nsecs;
  }
  kretprobe:tcp_sendmsg /@start[tid]/ {
    @latency = hist(nsecs - @start[tid]);
    delete(@start[tid]);
  }'

# Trace file I/O for a specific process
kubectl trace run node-1 -e '
  tracepoint:syscalls:sys_enter_openat {
    printf("%s opening: %s\n", comm, str(args->filename));
  }'

# List running traces
kubectl trace list

# Stop a specific trace
kubectl trace stop <trace-id>
```

### How It Works

kubectl-trace schedules a trace job as a Kubernetes Job on the target node. The job runs the bpftrace program using the host's kernel capabilities. Results are streamed back through the Kubernetes API. This approach requires nodes to have eBPF support (Linux kernel 4.9+ with BPF JIT enabled).

### When to Use kubectl-trace

- **Performance profiling**: Identifying slow system calls, network latency, or disk I/O bottlenecks
- **Security auditing**: Monitoring file access patterns, network connections, or process execution
- **Production safety**: Observing running applications without injecting any containers or modifying workloads
- **Kernel-level debugging**: Issues that require visibility into kernel behavior (TCP stack, scheduler, memory management)

## Kubernetes Native Ephemeral Containers

**Ephemeral Containers** are a built-in Kubernetes feature (GA since v1.23) that lets you add temporary debugging containers to running pods. Unlike regular containers, ephemeral containers cannot define ports, resources, or restart policies — they exist solely for debugging.

### Key Features

- **Native Kubernetes feature**: No plugins, CRDs, or additional software needed — works with `kubectl debug` (built-in, not the aylei plugin).
- **Target container specification**: Attach to a specific container's namespace using `--target`.
- **Profile support**: Use `--profile=syscall`, `--profile=netadmin`, or `--profile=baseline` to control capabilities.
- **Same image flexibility**: Use any container image — including specialized debug images like `nicolaka/netshoot` or `busybox`.
- **Automatic cleanup**: Ephemeral containers are removed when the pod is deleted or when manually removed.

### Usage Examples

```bash
# Start an ephemeral debug container
kubectl debug my-pod -it --image=ubuntu --share-processes

# Attach to a specific container's namespace
kubectl debug my-pod -it --image=nicolaka/netshoot --target=app

# Create an ephemeral container with a specific command
kubectl debug my-pod -it --image=busybox --target=app -- sh -c "cat /etc/resolv.conf"

# Copy an existing container's config as a debug target
kubectl debug my-pod -it --copy-to=my-pod-debug --container=app

# Debug a node (create a pod with host namespace access)
kubectl debug node/node-1 -it --image=ubuntu -- chroot /host
```

### How It Works

Ephemeral containers are added to the pod spec via the Kubernetes API's `/ephemeralcontainers` subresource. They share namespaces with the target container and run alongside it. The kubelet creates the container without restarting existing containers in the pod.

### When to Use Native Ephemeral Containers

- **Standard Kubernetes environments**: No need for third-party plugins or CRDs
- **Quick debugging**: Immediate access with a single `kubectl debug` command
- **Multi-container pods**: Target specific containers within complex pod layouts
- **Node-level debugging**: Access host namespaces for node-level troubleshooting
- **Air-gapped environments**: No external plugin installation required

## Choosing the Right Debugging Tool

| Scenario | Recommended Tool |
|----------|-----------------|
| Quick network debugging | kubectl-debug or native ephemeral |
| System call tracing | kubectl-trace (non-invasive) |
| Production performance profiling | kubectl-trace (eBPF) |
| Filesystem inspection | kubectl-debug or native ephemeral |
| No cluster modifications allowed | Native ephemeral containers |
| Kernel-level diagnostics | kubectl-trace |
| Custom debug environment | kubectl-debug or native ephemeral |
| Node-level troubleshooting | Native ephemeral (`kubectl debug node`) |
| Legacy clusters (<1.23) | kubectl-debug |

## Why Self-Host Your Kubernetes Debugging Tools?

**No external dependencies**: Self-hosted debugging tools run entirely within your cluster. You don't need to send pod logs, metrics, or traces to external SaaS platforms for analysis. This is critical for environments with strict data residency requirements.

**Cost savings**: Commercial Kubernetes debugging and observability platforms (like Datadog, New Relic, or Dynatrace) charge per node or per container. Self-hosted tools like kubectl-trace and native ephemeral containers are free and open-source.

**Full access to cluster internals**: Self-hosted debugging gives you direct access to kernel-level diagnostics (via eBPF), container namespaces, and node filesystems — capabilities that are often limited or unavailable in managed debugging services.

**Customization**: You can build custom debug images with your organization's specific tools — internal monitoring scripts, proprietary diagnostic utilities, or compliance audit tools — and use them across all debugging sessions.

For broader Kubernetes debugging approaches, see our [comprehensive debugging tools guide](../2026-04-25-stern-vs-kubetail-vs-inspektor-gadget-vs-kubectl-trace-kubernetes-debugging-tools-guide-2026/). For ephemeral preview environments, check our [dev environment comparison](../2026-05-03-okteto-vs-devspace-vs-telepresence-self-hosted-ephemeral-preview-environments-guide/).

## FAQ

### What is the difference between kubectl-debug (plugin) and kubectl debug (native)?

`kubectl debug` (native, built into kubectl since v1.23) uses Kubernetes ephemeral containers — a native API feature. `kubectl-debug` (the aylei plugin) creates a separate debug pod that shares namespaces with the target. Both achieve similar goals, but the native approach requires no additional software and is the recommended method for Kubernetes 1.23+.

### Does kubectl-trace require any changes to the target pod?

No. kubectl-trace uses eBPF to observe kernel behavior from outside the container. It does not inject containers, modify pod specs, or require any changes to the running application. This makes it the safest option for production debugging.

### Can I use ephemeral containers in production?

Yes. Ephemeral containers are a GA feature in Kubernetes 1.23+. However, be aware that adding an ephemeral container modifies the pod spec, which may trigger admission webhooks or policy engines. Also, ephemeral containers consume node resources (memory, CPU) while running.

### What kernel version is required for kubectl-trace?

kubectl-trace requires Linux kernel 4.9+ with BPF and BPF JIT support enabled. Most modern Linux distributions (Ubuntu 20.04+, RHEL 8+, Debian 11+) meet this requirement. You can check with `uname -r` and verify BPF support with `cat /boot/config-$(uname -r) | grep CONFIG_BPF`.

### How do I debug a CrashLoopBackOff pod?

For pods in CrashLoopBackOff, use `kubectl debug` with `--copy-to` to create a copy of the pod spec that you can modify: `kubectl debug my-pod --copy-to=debug-pod --container=app`. This creates a new pod with the same configuration but with a debug container attached, allowing you to inspect the filesystem and configuration without the original container crashing.

### Can kubectl-trace trace network traffic between pods?

Yes. kubectl-trace can attach eBPF probes to network-related kernel tracepoints (like `tcp:tcp_retransmit_skb`, `net:netdev_queue`) to observe network behavior at the kernel level. For application-level HTTP tracing, you can use kprobe probes on socket-related system calls.

### Do ephemeral containers persist after the debugging session?

Ephemeral containers persist until the pod is deleted or until you manually remove them. They do not automatically disappear when your kubectl session ends. To remove an ephemeral container, you need to edit the pod's ephemeralcontainers subresource or delete and recreate the pod.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Kubernetes Pod Debugging: kubectl-debug vs kubectl-trace vs Ephemeral Containers (2026)",
  "description": "Compare self-hosted Kubernetes pod debugging approaches: kubectl-debug for sidecar injection, kubectl-trace for eBPF-based observability, and native ephemeral containers.",
  "datePublished": "2026-05-21",
  "dateModified": "2026-05-21",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://hopkdj.github.io/openswap-guide/logo.png"
    }
  }
}
</script>
