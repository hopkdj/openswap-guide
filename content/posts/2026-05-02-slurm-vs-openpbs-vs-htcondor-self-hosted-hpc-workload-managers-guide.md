---
title: "Self-Hosted HPC Workload Managers: Slurm vs OpenPBS vs HTCondor Guide"
date: 2026-05-02
tags: ["comparison", "guide", "self-hosted", "hpc", "cluster", "scheduling"]
draft: false
---

High Performance Computing (HPC) clusters require sophisticated workload managers to schedule jobs, allocate resources, and maximize throughput across hundreds or thousands of compute nodes. Whether you run a research cluster, an ML training farm, or a rendering pipeline, choosing the right workload manager is critical.

This guide compares three leading open-source HPC workload managers: **Slurm**, **OpenPBS**, and **HTCondor** — helping you pick the right tool for your cluster.

## Quick Comparison Table

| Feature | Slurm | OpenPBS | HTCondor |
|---|---|---|---|
| GitHub Stars | ~3,946 | ~792 | ~314 |
| Primary Focus | HPC job scheduling | Batch job management | High-throughput computing |
| Scheduling Model | Priority-based, backfill | FIFO with priorities | Matchmaking, opportunistic |
| Resource Types | CPU, GPU, memory, nodes | CPU, memory, nodes | CPU, memory, storage |
| Multi-Cluster | Yes (federation) | Via job routing | Yes (flocking) |
| Web UI | Slurm-web, Open OnDemand | PBS Professional Web UI | Open OnDemand, condor_web |
| License | GPLv2 | PostgreSQL License | Apache 2.0 |
| Container Support | Yes (container plugin) | Yes (Docker/Singularity) | Yes (Docker/Singularity) |
| GPU Scheduling | Native (gres) | Via resources | Via machine ads |
| Active Development | Very active | Active | Active |

## Slurm — The Industry Standard

[Slurm](https://slurm.schedmd.com/) (Simple Linux Utility for Resource Management) is the most widely deployed HPC workload manager in the world. It powers over 60% of the TOP500 supercomputers, including the world's fastest systems.

### Key Features

- **Fast scheduling**: Sub-second scheduling decisions for large clusters
- **Backfill scheduling**: Maximizes utilization by fitting smaller jobs into gaps
- **Resource limits**: Fine-grained control over CPU, memory, GPU, and node allocation
- **Job arrays**: Submit thousands of similar jobs with a single command
- **Federation**: Connect multiple Slurm clusters for cross-cluster job submission
- **GPU support**: Generic resource (gres) plugin for native GPU scheduling
- **Container integration**: Supports Singularity, Charliecloud, and Shifter

### Installation

Slurm is typically installed via package manager on the controller and compute nodes:

```bash
# On Ubuntu/Debian (controller)
sudo apt update
sudo apt install -y slurmctld slurmdbd munge
sudo systemctl enable --now munge slurmctld slurmdbd

# On compute nodes
sudo apt install -y slurmd munge
sudo systemctl enable --now munge slurmd
```

### Docker Deployment

While Slurm is traditionally deployed on bare metal, you can run it in Docker for development and testing:

```yaml
version: "3.8"
services:
  slurmctld:
    image: slurmurm/slurmctld:latest
    container_name: slurmctld
    hostname: slurmctld
    environment:
      - SLURM_CLUSTER_NAME=mycluster
      - SLURM_NODELIST=compute[1-2]
      - SLURM_PARTITION=compute,compute[1-2]
    volumes:
      - slurm-state:/etc/slurm
      - /var/run/munge/munge.socket.2:/var/run/munge/munge.socket.2
    networks:
      slurm-net:
        ipv4_address: 10.10.0.2

  compute1:
    image: slurmurm/slurmd:latest
    container_name: compute1
    hostname: compute1
    environment:
      - SLURM_CLUSTER_NAME=mycluster
      - SLURMD_NODENAME=compute1
    depends_on:
      - slurmctld
    networks:
      slurm-net:
        ipv4_address: 10.10.0.3

  compute2:
    image: slurmurm/slurmd:latest
    container_name: compute2
    hostname: compute2
    environment:
      - SLURM_CLUSTER_NAME=mycluster
      - SLURMD_NODENAME=compute2
    depends_on:
      - slurmctld
    networks:
      slurm-net:
        ipv4_address: 10.10.0.4

volumes:
  slurm-state:

networks:
  slurm-net:
    driver: bridge
    ipam:
      config:
        - subnet: 10.10.0.0/24
```

### Configuration Example

A minimal `slurm.conf` for a small cluster:

```ini
ClusterName=mycluster
ControlMachine=slurmctld
SlurmctldPort=6817
SlurmdPort=6818
AuthType=auth/munge
StateSaveLocation=/var/lib/slurmctld
SlurmdSpoolDir=/var/lib/slurmd

# Nodes
NodeName=compute[1-2] CPUs=8 RealMemory=16000 State=UNKNOWN

# Partition
PartitionName=compute Nodes=compute[1-2] Default=YES MaxTime=INFINITE State=UP
```

### Reverse Proxy Setup (Nginx)

For web UI access via Slurm-web or Open OnDemand:

```nginx
server {
    listen 80;
    server_name slurm.example.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## OpenPBS — The Flexible Alternative

[OpenPBS](https://openpbs.org/) is an open-source batch queuing system originally developed by NASA. It manages job queues, allocates resources, and provides fair-share scheduling for compute clusters.

### Key Features

- **Job arrays**: Submit parameterized job collections
- **Routing queues**: Automatically route jobs to appropriate execution queues
- **Fair-share scheduling**: Balance resource allocation across users and groups
- **Mom hooks**: Custom Python hooks for job lifecycle events
- **Resource limits**: Control CPU, memory, walltime, and custom resources
- **Job dependencies**: Chain jobs with before/after dependencies
- **Checkpoint/restart**: Save and resume long-running jobs

### Installation

```bash
# On Ubuntu/Debian
sudo apt update
sudo apt install -y openpbs-server openpbs-execution
sudo systemctl enable --now pbs

# Initialize PBS
. /etc/pbs.conf
sudo -u pbs /opt/pbs/bin/qmgr -c "create server"
sudo /opt/pbs/bin/qmgr -c "set server scheduling=true"
sudo /opt/pbs/bin/qmgr -c "set queue batch resources_default.walltime = 24:00:00"
```

### Docker Deployment

```yaml
version: "3.8"
services:
  pbs-server:
    image: linuxserver/openpbs:latest
    container_name: pbs-server
    hostname: pbs-server
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Etc/UTC
    ports:
      - "15001:15001"  # PBS Mom
      - "15002:15002"  # PBS Server
    volumes:
      - pbs-config:/etc/pbs.conf
      - pbs-data:/var/spool/pbs
    networks:
      pbs-net:
        ipv4_address: 10.20.0.2

volumes:
  pbs-config:
  pbs-data:

networks:
  pbs-net:
    driver: bridge
```

## HTCondor — High-Throughput Computing

[HTCondor](https://research.cs.wisc.edu/htcondor/) (formerly Condor) specializes in high-throughput computing — maximizing the total number of jobs completed over time, especially in environments with heterogeneous resources and opportunistic scheduling.

### Key Features

- **Matchmaking**: ClassAds system matches job requirements with machine capabilities
- **Opportunistic computing**: Utilize idle desktop/workstation cycles
- **Flocking**: Connect multiple Condor pools for resource sharing
- **Job checkpointing**: Automatic checkpoint and migration of jobs
- **File transfer**: Automatic input/output file staging
- **DAGMan**: Workflow manager for complex job dependencies
- **High availability**: Central manager failover support

### Installation

```bash
# On Ubuntu/Debian
sudo apt update
sudo apt install -y htcondor

# Configure as central manager
sudo systemctl enable --now condor

# Set up the pool
sudo condor_config_val -write DAEMON_LIST "MASTER, COLLECTOR, NEGOTIATOR, SCHEDD"
sudo systemctl restart condor
```

### Docker Deployment

```yaml
version: "3.8"
services:
  condor-central:
    image: htcondor/execute:latest
    container_name: condor-central
    hostname: condor-central
    environment:
      - CONDOR_HOST=condor-central
      - COLLECTOR_HOST=condor-central
      - NEGOTIATOR_HOST=condor-central
    volumes:
      - condor-config:/etc/condor
      - condor-spool:/var/lib/condor/spool
    networks:
      condor-net:
        ipv4_address: 10.30.0.2

  condor-execute:
    image: htcondor/execute:latest
    container_name: condor-execute
    hostname: condor-execute
    environment:
      - CONDOR_HOST=condor-central
    depends_on:
      - condor-central
    networks:
      condor-net:
        ipv4_address: 10.30.0.3

volumes:
  condor-config:
  condor-spool:

networks:
  condor-net:
    driver: bridge
```

## Choosing the Right Workload Manager

### Use Slurm When:
- You need the industry standard with the largest community
- You manage a homogeneous HPC cluster with dedicated nodes
- You need advanced scheduling features (backfill, preemption, QoS)
- You require GPU and specialized resource scheduling

### Use OpenPBS When:
- You need flexible queue routing and fair-share policies
- You want a mature, well-documented system with Python hooks
- Your workload is primarily batch processing with predictable runtimes
- You need strong integration with existing PBS workflows

### Use HTCondor When:
- You have heterogeneous resources (desktops, workstations, servers)
- You want to opportunistically use idle compute cycles
- You need sophisticated job matchmaking with ClassAds
- Your focus is on throughput (total jobs completed) rather than latency

## Why Self-Host Your HPC Infrastructure?

Running your own workload manager gives you complete control over job scheduling policies, resource allocation, and cluster configuration. Self-hosted HPC tools eliminate vendor lock-in and per-core licensing fees that commercial schedulers charge.

For container orchestration on smaller clusters, see our [Kubernetes vs Docker Swarm vs Nomad comparison](../kubernetes-vs-docker-swarm-vs-nomad/). If you're managing Kubernetes clusters and need job scheduling within them, check our [workflow orchestration guide](../dagu-vs-netflix-conductor-vs-airflow-self-hosted-workflow-orchestration-guide-2026/). For server deployment and management automation, our [Ansible UI comparison](../semaphore-vs-awx-vs-rundeck-self-hosted-ansible-ui-guide-2026/) covers complementary tools.

## FAQ

### What is a workload manager?

A workload manager (also called a job scheduler or batch system) is software that manages the execution of computational jobs on a cluster. It receives job submissions, queues them, allocates resources (CPU, memory, nodes), schedules execution, and tracks job completion. Without a workload manager, users would need to manually coordinate which jobs run on which nodes and when.

### Is Slurm free and open source?

Yes, Slurm is released under the GPLv2 license and is free to use. The core scheduler, resource manager, and all standard plugins are open source. Some advanced features and commercial support are available through SchedMD, but the open-source version is production-ready and powers the majority of the world's fastest supercomputers.

### Can I run HPC workloads on Docker containers?

Yes, all three workload managers support containerized jobs. Slurm has native container plugins for Singularity and Charliecloud. OpenPBS can launch Docker and Singularity containers through job hooks. HTCondor supports Docker universe jobs that automatically handle container lifecycle. For development and testing, you can also run the workload managers themselves in Docker (see configurations above).

### How do I monitor my HPC cluster?

You can use Slurm-web for Slurm, the PBS `qstat` and `showq` commands for OpenPBS, or `condor_status` and `condor_q` for HTCondor. For broader infrastructure monitoring that covers the underlying nodes, tools like Netdata, Prometheus, and Zabbix can track node health, temperature, and resource utilization. See our [GPU monitoring guide](../nvtop-vs-dcgm-exporter-vs-netdata-self-hosted-gpu-monitoring-guide-2026/) for hardware-level monitoring.

### What's the difference between HPC and HTC?

HPC (High Performance Computing) focuses on maximizing the speed of individual jobs — running large simulations or calculations as fast as possible using many cores. HTC (High Throughput Computing) focuses on maximizing the total number of jobs completed over time, even if individual jobs run slower. Slurm and OpenPBS are primarily HPC-oriented, while HTCondor specializes in HTC.

### Can these tools manage GPU clusters?

Yes. Slurm has native GPU support through the Generic RESource (GRES) plugin, which tracks GPU availability and assigns GPUs to jobs. OpenPBS can manage GPUs as custom resources defined in the server configuration. HTCondor uses the machine's ClassAd to advertise available GPUs and match them to jobs that require them.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted HPC Workload Managers: Slurm vs OpenPBS vs HTCondor Guide",
  "description": "Compare three leading open-source HPC workload managers — Slurm, OpenPBS, and HTCondor — with installation guides, Docker configs, and scheduling feature comparisons.",
  "datePublished": "2026-05-02",
  "dateModified": "2026-05-02",
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
