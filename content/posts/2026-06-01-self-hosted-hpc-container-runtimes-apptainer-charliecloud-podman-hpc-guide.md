---
title: "Self-Hosted HPC Container Runtimes: Apptainer vs Charliecloud vs Podman-HPC Guide 2026"
date: "2026-06-01"
tags: ["hpc", "containers", "apptainer", "singularity", "charliecloud", "podman", "self-hosted", "scientific-computing", "infrastructure"]
draft: false
description: "Compare Apptainer, Charliecloud, and Podman-HPC for HPC container workloads. Learn which runtime best fits your scientific computing environment with benchmarks, configs, and deployment guides."
---

## Why Self-Host HPC Container Runtimes?

High-Performance Computing (HPC) centers face a unique containerization challenge: traditional container runtimes like Docker assume root privileges, daemon-based architectures, and layered filesystem overlays that conflict with shared, multi-tenant HPC clusters. HPC-specific container runtimes solve these problems by supporting unprivileged execution, parallel filesystem compatibility, and MPI integration out of the box.

Running your own HPC container runtime on a self-hosted cluster gives you full control over the software environment without relying on cloud container registries or managed Kubernetes services. Researchers can package their entire application stack — dependencies, libraries, and compiled binaries — into a single portable image that runs identically on the login node, compute nodes, and even their local workstation. This reproducibility is critical for scientific computing where results must be verifiable across different hardware generations and system configurations.

For workload orchestration on HPC clusters, see our [HPC Workload Managers comparison](../2026-05-02-slurm-vs-openpbs-vs-htcondor-self-hosted-hpc-workload-managers-guide/). If you need general-purpose container runtimes for non-HPC environments, check our [container runtimes guide](../containerd-vs-cri-o-vs-podman-self-hosted-container-runtimes-guide-2026/). For container virtualization at the OS level, our [LXD vs Incus vs Podman comparison](../2026-04-24-incus-vs-lxd-vs-podman-self-hosted-container-virtualization-guide-2026/) covers those options.

## HPC Container Runtime Comparison

| Feature | Apptainer (Singularity) | Charliecloud | Podman-HPC |
|---------|------------------------|--------------|------------|
| **Origin** | Lawrence Berkeley / Sylabs | Los Alamos National Lab | NERSC / Red Hat |
| **GitHub Stars** | 1,849 | 317 | 57 (NERSC) |
| **Rootless by Default** | Yes | Yes | Yes |
| **Image Format** | SIF (single file) | Tarball / SquashFS | OCI (Docker-compatible) |
| **MPI Support** | Native (host MPI) | Native (host MPI) | OCI hooks |
| **GPU Support** | NVIDIA/AMD (--nv/--rocm) | NVIDIA (--gpu) | NVIDIA (--gpus) |
| **Image Building** | Requires root/sandbox | Fully unprivileged | unprivileged (podman build) |
| **Parallel FS Compatible** | Yes (SIF is single file) | Yes (SquashFS) | Requires configuration |
| **OCI/Docker Compatible** | Partial (SIF conversion) | No (tarball) | Native (full OCI) |
| **Last Updated** | May 2026 | May 2025 (moved to GitLab) | May 2026 |

## Apptainer (formerly Singularity)

Apptainer is the most widely adopted HPC container runtime. Originally developed as Singularity at Lawrence Berkeley National Lab, it forked in 2021 with the community-driven Apptainer project joining the Linux Foundation while Sylabs maintains the commercial SingularityPRO. Apptainer's signature feature is the SIF (Singularity Image Format) — a single, cryptographically signed file that contains the entire container filesystem. This design eliminates the layered overlay issues that plague Docker on parallel filesystems like Lustre and GPFS.

### Installing Apptainer

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y apptainer

# RHEL/Rocky Linux
sudo dnf install -y epel-release
sudo dnf install -y apptainer

# Verify installation
apptainer --version
```

### Building and Running Containers

```bash
# Pull from Docker Hub and convert to SIF
apptainer pull docker://python:3.11-slim

# Run with GPU support and bind mounts
apptainer run --nv --bind /scratch:/data python_3.11-slim.sif

# Run an MPI job via Slurm
srun -N 4 apptainer exec --nv mpi_app.sif /opt/app/bin/simulation
```

Apptainer integrates natively with Slurm and other HPC schedulers. It supports NVIDIA GPUs via `--nv`, AMD GPUs via `--rocm`, and InfiniBand/RoCE networking transparently by passing through the host's MPI installation. The SIF format is also ideal for archival and sharing — a single file can be copied to any node without worrying about filesystem metadata overhead.

## Charliecloud

Charliecloud, developed at Los Alamos National Laboratory, takes a fundamentally different approach: it uses standard Linux user namespaces to provide unprivileged container execution without any setuid helper or daemon. Unlike Apptainer's SIF format, Charliecloud works with simple tarballs or SquashFS images — formats that require no special tooling to create or inspect.

### Installing Charliecloud

```bash
# Build from source (requires user namespace support)
git clone --recursive https://github.com/hpc/charliecloud.git
cd charliecloud
make
sudo make install PREFIX=/usr/local

# Verify
ch-run --version
```

### Building and Running Containers

```bash
# Build from Dockerfile (fully unprivileged)
ch-image build -t myapp -f Dockerfile .

# Flatten to squashfs for cluster deployment
ch-image build --force=seccomp -t myapp . 
ch-convert myapp /scratch/images/myapp.sqfs

# Run on compute node
ch-run /scratch/images/myapp.sqfs -- /opt/app/start.sh

# With GPU and MPI
ch-run --gpu -b /scratch:/data /scratch/images/myapp.sqfs -- mpirun /opt/app/sim
```

Charliecloud's key strength is its fully unprivileged build process. Researchers can create images on the login node without ever requesting root access — a critical requirement for many HPC centers. The tarball/SquashFS approach also means images can be stored on any parallel filesystem without the metadata overhead that Docker's layered storage would cause. The project moved its primary development to GitLab in 2025 but remains actively maintained.

## Podman-HPC

Podman-HPC, developed at NERSC (National Energy Research Scientific Computing Center), bridges the gap between enterprise OCI containers and HPC requirements. It wraps standard Podman (the daemonless Docker alternative) with HPC-specific features: automatic container launch across MPI ranks, SquashFS-based image caching for parallel filesystems, and transparent UID/GID mapping for shared cluster environments.

### Installing Podman-HPC

```bash
# Install Podman first
sudo apt install -y podman  # Ubuntu/Debian
sudo dnf install -y podman  # RHEL/Rocky

# Install podman-hpc from NERSC
git clone https://github.com/NERSC/podman-hpc.git
cd podman-hpc
sudo make install

# Configure for HPC
export PODMANHPC_IMG_STORE=/scratch/$USER/podman-hpc-images
podman-hpc migrate
```

### Running MPI Workloads with Podman-HPC

```bash
# Pull image once
podman-hpc pull docker://nvcr.io/nvidia/hpc-benchmarks:24.03

# Run across MPI ranks via Slurm
srun -N 4 --ntasks-per-node=8 podman-hpc run --gpu \
    --mount type=bind,src=/scratch,dst=/data \
    nvcr.io/nvidia/hpc-benchmarks:24.03 \
    mpirun /opt/hpc-benchmarks/hpl

# Interactive session
podman-hpc shell --gpu nvcr.io/nvidia/cuda:12.4-devel-ubuntu22.04
```

Podman-HPC's key advantage is full OCI compatibility — any image from Docker Hub, NVIDIA NGC, or Quay.io works without conversion. The `podman-hpc migrate` command converts images to SquashFS for efficient parallel filesystem storage. NERSC has deployed Podman-HPC on Perlmutter, one of the world's top supercomputers, proving it scales to thousands of nodes.

## Deployment Architecture

A typical HPC container runtime deployment follows this pattern:

```
[Login Node]                    [Compute Nodes]
     |                                |
apptainer pull              apptainer run --nv
ch-image build              ch-run --gpu
podman-hpc pull             podman-hpc run --gpu
     |                                |
     v                                v
[Shared Parallel FS]        [Local SSD / tmpfs]
/scratch/images/*.sif       Container extracted at runtime
/scratch/images/*.sqfs      
```

The key architectural difference from Docker/Kubernetes is the absence of a long-running daemon. HPC container runtimes are invoked directly by the batch scheduler (Slurm, PBS, etc.) on each compute node, with the container image stored on the shared parallel filesystem. This eliminates the single point of failure and network bottleneck of a centralized registry.

## Choosing the Right HPC Container Runtime

**Choose Apptainer if:** You need the broadest ecosystem support, SIF image signing for trusted production pipelines, native integration with major HPC schedulers, and you have access to root or fakeroot for image building on a dedicated build node.

**Choose Charliecloud if:** Your center prohibits any setuid binaries or privileged operations entirely, researchers need to build images completely unprivileged on login nodes, and you value architectural simplicity over Docker compatibility.

**Choose Podman-HPC if:** Your workflows already use Docker images extensively, you need native OCI compatibility without conversion, you want a single container toolchain for both HPC and cloud environments, and your cluster uses Slurm or similar MPI-aware schedulers.

For environments that must support diverse user requirements, many centers deploy both Apptainer AND Podman-HPC — using Apptainer for traditional HPC workflows and Podman-HPC for cloud-native applications ported to the cluster.

## FAQ

### Can I run Docker images on HPC container runtimes?

Yes, all three runtimes support Docker/OCI images. Apptainer converts them to SIF format (`apptainer pull docker://image`), Podman-HPC uses them natively without conversion, and Charliecloud builds from Dockerfiles but stores as tarballs/SquashFS. Each conversion approach has tradeoffs in startup time, storage efficiency, and metadata handling on parallel filesystems.

### Do HPC container runtimes support GPU computing?

Yes, all three support NVIDIA GPUs. Apptainer uses `--nv` to bind-mount the NVIDIA driver stack, Charliecloud uses `--gpu`, and Podman-HPC uses `--gpu` (passed through to Podman). AMD GPU support is available in Apptainer via `--rocm` and is emerging in the other runtimes. Intel GPU support remains limited across all three.

### How do HPC containers handle MPI communication?

HPC container runtimes use a "hybrid" MPI model: the MPI library is NOT included in the container image. Instead, the container mounts the host's MPI installation at runtime. This means the MPI library version must match between the build environment and the target cluster. This design choice ensures compatibility with the cluster's high-speed interconnect (InfiniBand, Omni-Path, Slingshot) since the MPI implementation is optimized for the specific hardware.

### Are HPC containers secure on multi-tenant clusters?

Yes — this is a core design goal. All three runtimes operate completely without root privileges. They use Linux user namespaces to map the container's internal root to the invoking user's UID on the host. This means a user running a container on a shared login node cannot escalate privileges or access other users' files. Apptainer adds SIF image signing for supply chain verification.

### Can I use Kubernetes-style orchestration with HPC containers?

HPC containers are designed for batch-scheduled environments, not long-running orchestration. However, Podman-HPC can integrate with Kubernetes via the CRI-O runtime for hybrid architectures where some workloads run as services and others as batch jobs. For pure HPC workloads, direct Slurm/PBS integration is the standard approach — it avoids the overhead and complexity of a Kubernetes control plane.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted HPC Container Runtimes: Apptainer vs Charliecloud vs Podman-HPC Guide 2026",
  "description": "Compare Apptainer, Charliecloud, and Podman-HPC for HPC container workloads. Learn which runtime best fits your scientific computing environment with benchmarks, configs, and deployment guides.",
  "datePublished": "2026-06-01",
  "dateModified": "2026-06-01",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到科技监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测市场事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
