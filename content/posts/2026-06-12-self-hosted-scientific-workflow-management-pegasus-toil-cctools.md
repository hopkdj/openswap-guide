---
title: "Self-Hosted Scientific Workflow Management: Pegasus vs Toil vs Makeflow (CCTools)"
date: "2026-06-12"
tags: ["self-hosted", "comparison", "guide", "scientific-computing", "workflow", "hpc", "distributed-computing", "automation", "python", "java"]
draft: false
---

## Introduction

Scientific computing workflows often involve hundreds or thousands of interdependent computational steps — data preprocessing, simulations, statistical analyses, visualization — that must execute in a specific order across distributed computing resources. Scientific workflow management systems (SWMS) automate this orchestration, handling task dependencies, resource allocation, failure recovery, and provenance tracking.

This guide compares three open-source scientific workflow engines: **Pegasus**, a DAG-based workflow manager for large-scale distributed computing; **Toil**, a Python-based workflow engine supporting CWL and WDL standards; and **Makeflow**, part of the CCTools suite for managing task dependencies across clusters and clouds.

## What Are Scientific Workflow Systems?

Unlike CI/CD pipelines or business process workflow tools, scientific workflow systems are designed for data-intensive, compute-bound research workloads. They manage the flow of data through a series of computational steps — often spanning thousands of CPU cores across HPC clusters, cloud instances, and grid resources.

Key capabilities include:

- **Dependency management**: Automatically determine execution order from dataflow
- **Resource provisioning**: Request compute nodes, transfer data, execute tasks
- **Fault tolerance**: Retry failed tasks, resume interrupted workflows from checkpoints
- **Provenance tracking**: Record every step's inputs, outputs, parameters, and runtime
- **Portability**: Run the same workflow on different infrastructures without modification
- **Scalability**: From single-node tests to million-task production runs

## Tool Comparison

| Feature | Pegasus | Toil | Makeflow (CCTools) |
|---------|---------|------|---------------------|
| **Workflow Definition** | DAX (XML/Python API) | Python, CWL, WDL | Makefile-like syntax |
| **Execution Model** | DAG-based planning | Directed graph execution | Task dependency graph |
| **Resource Managers** | HTCondor, Slurm, PBS, LSF, Kubernetes, AWS, GCP | Slurm, Grid Engine, AWS, GCP, Azure, Kubernetes | HTCondor, Slurm, SGE, PBS, Work Queue |
| **Data Management** | Built-in staging & cleanup | FileStore with caching | Work Queue with data awareness |
| **Fault Tolerance** | Retry, rescue DAG, checkpoint | Job store with resume | Transaction log, retry |
| **Provenance** | Full workflow provenance DB | Job store history | Makeflow log |
| **Standards Support** | Custom (DAX) | CWL, WDL | Custom (Makefile-like) |
| **GitHub Stars** | 232+ | 932+ | 145+ |
| **Primary Language** | Java + Python | Python | C |
| **License** | Apache 2.0 | Apache 2.0 | GPL 2.0 |
| **Installation** | apt, Docker | pip, Docker | Source build |

## Pegasus: DAG-Based Planning and Execution

Pegasus (Planning for Execution in Grids) takes a unique "plan-then-execute" approach. Instead of executing tasks immediately, Pegasus first analyzes the abstract workflow, maps it to available resources, plans data transfers, and generates an executable DAG (Directed Acyclic Graph) optimized for the target infrastructure. This planning phase enables sophisticated optimizations like task clustering, data reuse, and performance prediction.

Pegasus has been used for workflows in astronomy (LIGO gravitational wave analysis), bioinformatics (genome sequencing pipelines), earthquake science (Southern California Earthquake Center), and climate modeling.

**Key features:**
- Separate planning and execution phases for optimization
- Abstract workflows independent of execution infrastructure
- Automatic data staging and cleanup between sites
- Hierarchical workflows (nested sub-workflows)
- Performance dashboard for monitoring
- Integration with HTCondor DAGMan for execution
- Support for containers (Docker, Singularity)

### Installing Pegasus

```bash
# Ubuntu/Debian
wget -O - https://download.pegasus.isi.edu/pegasus/gpg.txt | sudo apt-key add -
echo "deb https://download.pegasus.isi.edu/pegasus/ubuntu $(lsb_release -cs) main" | \
  sudo tee /etc/apt/sources.list.d/pegasus.list
sudo apt update
sudo apt install pegasus

# Verify
pegasus-version

# Or via pip for client tools
pip install pegasus-wms
```

### Defining a Pegasus Workflow (Python API)

```python
#!/usr/bin/env python3
from Pegasus.api import *

# Create the abstract workflow
wf = Workflow("genome-analysis")

# Define transformations (executables)
preprocess = Transformation("preprocess")
preprocess.add_sites(TransformationSite("condorpool", "/usr/bin/preprocess", is_stageable=True))

align = Transformation("align")
align.add_sites(TransformationSite("condorpool", "/usr/bin/align", is_stageable=True))

# Add input file
input_fasta = File("reference.fasta")

# Create jobs with dependencies
pre_job = Job(preprocess) \
    .add_args("-i", input_fasta, "-o", "preprocessed.fa") \
    .add_inputs(input_fasta) \
    .add_outputs(File("preprocessed.fa"))

align_job = Job(align) \
    .add_args("-r", "preprocessed.fa", "-o", "aligned.bam") \
    .add_inputs(File("preprocessed.fa")) \
    .add_outputs(File("aligned.bam"))

# Add jobs to workflow
wf.add_jobs(pre_job, align_job)

# Plan and run
wf.plan(submit=True)
```

### Running Pegasus

```bash
# Generate the DAG from the abstract workflow
pegasus-plan \
  --conf pegasus.conf \
  --dax workflow.dax \
  --dir submit \
  --output-site local \
  --sites condorpool

# Submit the generated DAG
pegasus-run submit/

# Monitor progress
pegasus-status submit/

# Analyze after completion
pegasus-statistics submit/
pegasus-analyzer submit/
```

## Toil: Python-Native Workflow Engine

Toil is a Python-based workflow engine that supports both native Python workflows and community-standard languages (CWL, WDL). Its key innovation is the **job store** abstraction: all workflow state — inputs, outputs, job definitions, and execution logs — is stored in a pluggable backend (file system, AWS S3, Google Cloud Storage, Azure Blob). This makes workflows inherently resumable: if a cluster node fails or a cloud instance is terminated, Toil restarts from the last checkpoint.

Toil is developed at the UC Santa Cruz Genomics Institute and is used for large-scale genomics workflows processing petabytes of sequencing data.

**Key features:**
- Single-machine or distributed execution with the same code
- Job store abstraction for resumable workflows
- FileStore with automatic caching and cleanup
- Native support for Docker containers
- CWL and WDL workflow language support
- Leader-worker architecture for distributed execution
- Python 3.8+ with rich API

### Installing Toil

```bash
# Quick install
pip install toil

# With CWL support
pip install "toil[cwl]"

# With WDL support
pip install "toil[wdl]"

# With AWS support
pip install "toil[aws]"

# Verify installation
toil --version
```

### Defining a Toil Workflow (Python)

```python
#!/usr/bin/env python3
from toil.common import Toil
from toil.job import Job

def preprocess(job, input_file_id):
    """Download input, process, upload output."""
    # Read input file from file store
    with job.fileStore.readGlobalFileStream(input_file_id) as f:
        data = f.read()
    
    # Process data
    processed = data.upper()
    
    # Write output to file store
    with job.fileStore.writeGlobalFileStream() as (out_fh, out_id):
        out_fh.write(processed.encode())
    
    return out_id

def analyze(job, processed_id):
    """Analyze preprocessed data."""
    with job.fileStore.readGlobalFileStream(processed_id) as f:
        data = f.read()
    
    # Analysis logic
    word_count = len(data.split())
    
    # Store results
    with job.fileStore.writeGlobalFileStream() as (out_fh, out_id):
        out_fh.write(f"Word count: {word_count}\n".encode())
    
    return out_id

if __name__ == "__main__":
    parser = Job.Runner.getDefaultArgumentParser()
    options = parser.parse_args()
    
    with Toil(options) as toil:
        # Import input file
        input_id = toil.importFile("file:///data/input.txt")
        
        # Create jobs with dependencies
        preprocess_job = Job.wrapJobFn(preprocess, input_id)
        analyze_job = Job.wrapJobFn(analyze, preprocess_job.rv())
        
        # Build the job graph
        preprocess_job.addChild(analyze_job)
        
        # Run the workflow
        output_id = toil.start(preprocess_job)
        
        # Export the final result
        toil.exportFile(output_id, "file:///data/output.txt")
```

### Running Toil Distributed

```bash
# Start the leader
toil leader \
  --provisioner=aws \
  --nodeType=t3.medium \
  --maxNodes=10 \
  --clusterName=my-workflow \
  my_workflow.py

# Or on an existing Slurm cluster
toil launch-cluster --provisioner=slurm --partition=compute toil-cluster
toil rsync-cluster --insecure toil-cluster my_workflow.py :/tmp/
toil ssh-cluster toil-cluster "python3 /tmp/my_workflow.py --jobStore file:///tmp/jobstore"
```

### Deploying Toil with Docker

```yaml
version: "3.8"
services:
  toil-leader:
    image: python:3.11-slim
    container_name: toil-leader
    working_dir: /workflows
    volumes:
      - ./workflows:/workflows
      - ./jobstore:/jobstore
      - ./data:/data
    environment:
      - TOIL_WORKDIR=/jobstore
    command: >
      bash -c "
        pip install toil &&
        python3 workflow.py --jobStore file:///jobstore
      "
    restart: "no"
```

## Makeflow (CCTools): Make-like Task Management

Makeflow is part of the Cooperative Computing Tools (CCTools) suite, developed at the University of Notre Dame. It uses a familiar Makefile-like syntax to define workflow dependencies, making it accessible to researchers already comfortable with GNU Make. Despite its simple interface, Makeflow can manage workflows spanning thousands of tasks across HPC clusters, clouds, and grids.

Makeflow's secret weapon is **Work Queue** — a master-worker framework that distributes tasks to worker processes running on any available compute resource. Workers can be started manually or automatically provisioned via resource managers.

**Key features:**
- Makefile-like workflow syntax (easy learning curve)
- Work Queue for distributed execution across heterogeneous resources
- Automatic data dependency tracking
- Transaction log for fault recovery
- Resource monitoring and dynamic load adjustment
- Integration with HTCondor, Slurm, PBS, SGE
- Support for nested Makefiles and remote task execution

### Installing CCTools (includes Makeflow)

```bash
# From source
git clone https://github.com/cooperative-computing-lab/cctools.git
cd cctools
./configure --prefix /opt/cctools
make -j$(nproc)
sudo make install

# Add to PATH
export PATH="/opt/cctools/bin:$PATH"

# Verify
makeflow -v
work_queue_worker -v
```

### Defining a Makeflow Workflow

Makeflow files use a syntax very similar to GNU Make:

```makefile
# Makeflow file: genome_analysis.mf

# Define executables
PREPROCESS = /usr/bin/preprocess
ALIGN = /usr/bin/align
ANALYZE = /usr/bin/analyze

# Workflow steps with dependencies
preprocessed.fa: reference.fasta
	$(PREPROCESS) -i reference.fasta -o preprocessed.fa

aligned.bam: preprocessed.fa reference.fasta
	$(ALIGN) -r reference.fasta -i preprocessed.fa -o aligned.bam

variants.vcf: aligned.bam reference.fasta
	$(ANALYZE) -b aligned.bam -r reference.fasta -o variants.vcf

# Final output
all: variants.vcf
```

### Running Makeflow

```bash
# Local execution (single machine)
makeflow -T local genome_analysis.mf

# Distributed execution with Work Queue
# Step 1: Start workers on compute nodes
work_queue_worker -M my-workflow --cores 4 &

# Step 2: Start the master (runs the workflow)
makeflow -T wq genome_analysis.mf

# With HTCondor
makeflow -T condor genome_analysis.mf

# With Slurm
makeflow -T slurm genome_analysis.mf

# Monitor progress
makeflow_monitor makeflow.makeflowlog

# Clean outputs for re-run
makeflow -c genome_analysis.mf
```

### Deploying Work Queue Workers with Docker

```yaml
version: "3.8"
services:
  wq-worker:
    image: cooperativecomputinglab/cctools:latest
    container_name: wq-worker
    command: >
      work_queue_worker
      -M my-project
      --cores 4
      --memory 8192
      --disk 50000
    deploy:
      replicas: 4
    restart: unless-stopped
```

## Why Self-Host Scientific Workflow Management?

**Reproducibility** is the foundation of scientific computing. Self-hosted workflow engines give you complete control over the execution environment — specific software versions, library dependencies, and system configurations. Unlike cloud workflow services where the underlying infrastructure changes without notice, your own workflow engine running on known hardware produces consistent, reproducible results across runs.

**Cost efficiency for large-scale computing** is dramatic. Cloud workflow services charge per-task execution fees that multiply quickly for million-task genomics or materials science workflows. Running Toil or Makeflow on your own HPC cluster or reserved cloud instances turns variable per-task costs into fixed infrastructure costs. Research groups processing terabytes of sequencing data daily save thousands of dollars per month by self-hosting.

**Data locality** matters when your workflows process sensitive research data. Medical imaging workflows handling patient data, defense research with classified datasets, and proprietary industrial simulations cannot leave the organization's network. Self-hosted workflow engines running within your security perimeter keep data where it belongs while still enabling distributed execution across internal compute resources.

**Flexibility across heterogeneous resources** is a key strength of self-hosted engines. Your organization may have a mix of HPC clusters, cloud burst instances, and departmental servers. Pegasus can plan workflows that optimally use all these resources simultaneously — something cloud-only workflow services cannot do. For organizations already using workflow orchestration tools — see our [Temporal, Camunda, and Flowable comparison](../temporal-vs-camunda-vs-flowable-self-hosted-workflow-orchestration-guide-2026/) for business process workflows — scientific workflow engines provide the HPC-specific features those tools lack. Our [reproducible research platforms guide](../2026-06-10-self-hosted-reproducible-research-binderhub-renku-stencila-guide/) covers the broader ecosystem of tools that complement workflow engines for computational research. For organizations building distributed infrastructure, our [distributed locking and coordination guide](../self-hosted-distributed-locking-etcd-zookeeper-consul-redis-guide-2026/) covers the coordination primitives that workflow engines rely on for distributed task management.

## Choosing the Right Scientific Workflow Engine

**Choose Pegasus** when you need sophisticated planning and optimization for heterogeneous, multi-site workflows. Its plan-then-execute model enables performance optimizations that reactive engines cannot achieve. Pegasus excels in environments where you have access to multiple computing sites (HPC cluster + cloud + local servers) and need to optimize data movement and task placement across them.

**Choose Toil** when you need Python-native workflow development with support for community standards (CWL, WDL). Its job store abstraction makes workflows inherently resumable — ideal for long-running genomics or ML training pipelines where node failures are expected. Toil's ability to run the same workflow code on a laptop for development and a cluster for production is a significant productivity advantage.

**Choose Makeflow (CCTools)** when you need a lightweight, Makefile-friendly workflow engine that can scale from a single workstation to thousands of cores. Its Work Queue architecture is particularly effective for harnessing idle cycles across heterogeneous resources — desktops, servers, and cluster nodes alike. Researchers already comfortable with GNU Make will find Makeflow immediately productive.

## Performance and Scaling Considerations

| Scenario | Pegasus | Toil | Makeflow |
|----------|---------|------|----------|
| **Task overhead** | ~1-5 sec (planning) | ~0.5-2 sec per job | ~0.1-0.5 sec per task |
| **Max tasks per workflow** | 1,000,000+ | 100,000+ | 10,000,000+ |
| **Concurrent tasks** | 10,000+ | 1,000+ | 100,000+ |
| **Data staging** | Automatic, optimized | FileStore with caching | Work Queue data awareness |
| **Multi-site support** | Native | Via cloud provisioner | Via Work Queue federation |
| **Memory per job** | ~50 MB (planner) | ~100 MB (worker) | ~20 MB (worker) |

For production deployments, plan resource allocation carefully. Pegasus workflows benefit from dedicated HTCondor pools for execution. Toil's leader process requires sufficient memory to track all running jobs (roughly 1KB per job). Makeflow's Work Queue workers are extremely lightweight and can run on resource-constrained nodes.

## FAQ

### Can I convert between these workflow formats?

Partial conversion is possible but not seamless. Toil supports importing CWL and WDL workflows, giving you a migration path from those standards. Pegasus can execute workflows defined via its Python API or DAX format. Makeflow uses its own Makefile-like syntax. For cross-engine portability, define your workflow steps as standalone executables or container images, then write engine-specific wrapper scripts that call the same executables.

### How do these compare to Nextflow or Snakemake?

Nextflow and Snakemake are both excellent workflow systems focused on bioinformatics and data science. Nextflow uses a Groovy-based DSL with built-in container support, while Snakemake uses Python-based rule definitions. The tools in this comparison serve a broader scientific computing audience: Pegasus for multi-site HPC optimization, Toil for Python-native workflows with cloud portability, and Makeflow for maximum simplicity at scale.

### What happens when a node fails mid-workflow?

All three engines handle node failures gracefully. Pegasus generates rescue DAGs that retry only failed tasks. Toil's job store preserves all state, enabling restart from the last successful checkpoint. Makeflow uses a transaction log to track completed tasks and retries only unsuccessful ones. None of the three re-executes completed work after a failure.

### Can these run on a single machine for development?

Yes, all three support single-machine execution. Toil runs without any distributed infrastructure by default — the same code that runs on a laptop runs on a cluster. Makeflow supports `-T local` mode for testing. Pegasus can plan and execute workflows locally using a personal HTCondor installation. This makes development and testing straightforward before scaling to production.

### How do I handle software dependencies in my workflows?

Containerization is the recommended approach. Package each workflow step as a Docker or Singularity container with its dependencies. Pegasus, Toil, and Makeflow all support container-based execution. Toil has native Docker integration via its `--container` flag. Makeflow supports containers through wrapper scripts. Pegasus supports Docker and Singularity through its transformation catalog.

### What about workflow monitoring and dashboards?

Pegasus includes a monitoring dashboard (`pegasus-dashboard`) that tracks workflow progress, resource usage, and performance metrics. Toil provides a web-based job store browser (`toil server`) for inspecting workflow state. Makeflow logs can be analyzed with `makeflow_monitor` and `makeflow_graph` for visualization. For comprehensive monitoring, integrate with your existing infrastructure — see our [distributed tracing comparison](../signoz-jaeger-uptrace-self-hosted-apm-distributed-tracing-guide/) for observability tools.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Scientific Workflow Management: Pegasus vs Toil vs Makeflow (CCTools)",
  "description": "Compare Pegasus, Toil, and Makeflow (CCTools) for self-hosted scientific workflow management. Installation guides, workflow examples, and HPC deployment patterns included.",
  "datePublished": "2026-06-12",
  "dateModified": "2026-06-12",
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

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
