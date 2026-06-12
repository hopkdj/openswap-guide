---
title: "Self-Hosted HPC Scientific Workflow Orchestrators: FireWorks vs Parsl vs RADICAL-Pilot Compared 2026"
date: "2026-06-12"
tags: ["hpc", "workflow-orchestration", "scientific-computing", "fireworks", "parsl", "radical-pilot", "job-scheduling"]
draft: false
---

## Introduction

Modern scientific computing involves complex pipelines: data preprocessing, simulation runs, post-processing analysis, and visualization — often across multiple computing platforms from local clusters to cloud resources. Scientific workflow orchestrators manage these multi-step computational workflows, handling job dependencies, resource provisioning, and failure recovery automatically.

This article compares three leading open-source scientific workflow orchestration frameworks designed for HPC environments: **FireWorks**, **Parsl**, and **RADICAL-Pilot**.

## Why Self-Host a Scientific Workflow Orchestrator?

Scientific computing workflows differ fundamentally from business process automation or CI/CD pipelines. They require specialized features that general-purpose workflow tools lack:

**Heterogeneous resource management**: A single scientific workflow may need to run jobs on an HPC cluster (via Slurm/PBS), a cloud VM (via AWS/Azure), and a local workstation — all within the same pipeline. Scientific orchestrators abstract away the job submission details, presenting a unified interface across resources.

**Dynamic workflow generation**: Unlike static DAGs in tools like Airflow, scientific workflows often need to generate new tasks based on intermediate results. A materials simulation might spawn hundreds of follow-up calculations depending on the initial screening results. This "dynamic workflow" pattern is native to scientific orchestrators.

**Checkpoint and restart**: Long-running simulations (days to weeks) need automatic checkpointing and the ability to resume from the last saved state after a node failure or preemption event. Scientific orchestrators track task completion at a fine granularity and only re-run what is necessary.

**High-throughput computing**: Screening millions of candidate molecules or running parameter sweeps across thousands of configurations requires orchestration of millions of independent tasks — far beyond what CI/CD workflow tools are designed for. For general-purpose workflow automation, see our [self-hosted workflow orchestration guide](../2026-04-24-dagu-vs-netflix-conductor-vs-airflow-self-hosted-workflow-orchestration-guide-2026/).

For machine learning-specific pipeline needs, check our [ML pipeline orchestration comparison](../2026-05-03-self-hosted-ml-pipeline-orchestration-kubeflow-metaflow-zenml-guide/). For managing the individual compute jobs themselves, see our [scientific workflow management guide](../2026-06-12-self-hosted-scientific-workflow-management-pegasus-toil-cctools/).

## Comparison Table

| Feature | FireWorks | Parsl | RADICAL-Pilot |
|---------|-----------|-------|---------------|
| **GitHub Stars** | 424+ | 616+ | 64+ |
| **Workflow Pattern** | Directed Acyclic Graph (DAG) | Python-native futures | Pilot-Job (task overlay) |
| **Dynamic Workflows** | Yes (Firetasks with children) | Yes (native Python logic) | Yes (task dependencies) |
| **Backend Support** | Slurm, PBS, SGE, IBM LSF | Slurm, PBS, SGE, Cobalt, AWS, Azure, GCP, Kubernetes | Slurm, PBS, SGE, LSF, AWS, GCP, Azure |
| **Job Types** | Script, command, multi-step | Python functions, bash, containers | MPI, OpenMP, GPU, multi-core |
| **Fault Tolerance** | Automatic rerun on failure | Retry with backoff | Pilot-level recovery |
| **Monitoring** | Web GUI + MongoDB backend | Live monitoring dashboard | RADICAL-Analytics toolkit |
| **License** | BSD-3-Clause | Apache-2.0 | MIT |
| **Last Updated** | April 2026 | June 2026 | May 2026 |

## FireWorks

FireWorks (materialsproject/fireworks, 424+ stars) was developed at Lawrence Berkeley National Laboratory to power the Materials Project — a database computing properties of millions of materials. It uses MongoDB as a centralized workflow database with a manager-worker architecture.

**Installation and Setup:**

```bash
# Install FireWorks
pip install fireworks

# Configure MongoDB backend (create ~/.fireworks/my_fworker.yaml)
cat > ~/.fireworks/my_fworker.yaml << 'EOF'
name: compute_node_01
category: ''
query: '{}'
EOF

# Create launchpad configuration
cat > ~/.fireworks/my_launchpad.yaml << 'EOF'
host: localhost
port: 27017
name: fireworks_db
username: null
password: null
EOF

# Define a workflow
cat > workflow.py << 'EOF'
from fireworks import Firework, Workflow, LaunchPad
from fireworks.user_objects.firetasks.script_task import ScriptTask

fw1 = Firework(
    ScriptTask.from_str('echo "Running simulation" && sleep 10'),
    name="simulation_step"
)
fw2 = Firework(
    ScriptTask.from_str('echo "Post-processing results"'),
    name="analysis_step"
)

# Create workflow with dependency
wf = Workflow([fw1, fw2], {fw1: [fw2]})

# Submit to launchpad
launchpad = LaunchPad.auto_load()
launchpad.add_wf(wf)
EOF

python workflow.py

# Start the Rocket launcher
rlaunch singleshot
```

FireWorks workflows are DAGs of Firetasks connected by dependency links. Each Firetask can spawn child Fireworks dynamically, enabling adaptive workflows where computational results determine subsequent steps. The web GUI provides real-time visualization of workflow state.

## Parsl

Parsl (parsl/parsl, 616+ stars) takes a Python-native approach — scientific workflows are written as regular Python programs with decorators marking parallel functions. This makes it the most accessible option for scientists who already work in Python.

**Installation and Usage:**

```bash
# Install Parsl
pip install parsl

# Example: parallel parameter sweep
cat > parsl_sweep.py << 'EOF'
import parsl
from parsl import python_app
from parsl.config import Config
from parsl.executors import HighThroughputExecutor
from parsl.providers import SlurmProvider

# Configure for Slurm cluster
config = Config(
    executors=[
        HighThroughputExecutor(
            label="hpc_workers",
            max_workers_per_node=2,
            provider=SlurmProvider(
                partition="compute",
                nodes_per_block=2,
                init_blocks=1,
                max_blocks=4,
                walltime="01:00:00"
            )
        )
    ]
)

parsl.load(config)

@python_app
def run_simulation(param):
    import time
    # Run actual simulation here
    time.sleep(5)
    return {"param": param, "result": param ** 2}

# Run 100 concurrent simulations
params = list(range(100))
futures = [run_simulation(p) for p in params]

# Collect results
results = [f.result() for f in futures]
print(f"Completed {len(results)} simulations")
EOF

python parsl_sweep.py
```

Parsl's key innovation is the **Parsl DataFlow Kernel (DFK)** which manages task dependencies transparently. When a task produces a value used by downstream tasks, Parsl handles the data transfer and scheduling automatically — no explicit DAG definition required. This is ideal for interactive computing where workflows evolve as you explore data.

## RADICAL-Pilot

RADICAL-Pilot (radical-cybertools/radical.pilot, 64+ stars) implements the Pilot-Job abstraction — it acquires a pool of compute resources first, then schedules tasks onto those resources. This architecture is particularly efficient for high-throughput computing with many short-duration tasks.

**Setup:**

```bash
# Install RADICAL-Pilot
pip install radical.pilot

# Example: Pilot-Job workflow
cat > radical_workflow.py << 'EOF'
import radical.pilot as rp
import radical.utils as ru

session = rp.Session()

# Define pilot (resource acquisition)
pd = rp.PilotDescription()
pd.resource = "local.localhost"
pd.cores = 8
pd.runtime = 30  # minutes

pilot = session.submit_pilots(pd)[0]

# Wait for pilot to become active
session.wait(pilot.state == rp.PMGR_ACTIVE)

# Create task descriptions
tds = []
for i in range(50):
    td = rp.TaskDescription()
    td.executable = "/bin/bash"
    td.arguments = ["-c", f"echo 'Task {i}' && sleep 2"]
    tds.append(td)

# Submit all tasks to the pilot
tasks = session.submit_tasks(tds)

# Wait for completion
session.wait([t.state == rp.DONE for t in tasks])
session.close()
EOF

python radical_workflow.py
```

RADICAL-Pilot's pilot-job model reduces queue wait times for high-throughput workloads. Instead of submitting 10,000 individual Slurm jobs (each incurring queue delays and scheduler overhead), a single pilot job acquires 100 nodes and RADICAL-Pilot manages task placement internally. This achieves near-linear scaling for ensemble workloads across 10,000+ cores.

## Choosing the Right Orchestrator

| Use Case | Recommended Tool |
|----------|-----------------|
| Materials science, chemistry workflows | FireWorks |
| Interactive Python-based analysis | Parsl |
| High-throughput computing (millions of tasks) | RADICAL-Pilot |
| Mixed HPC + cloud workflows | Parsl |
| Workflows with complex DAGs and checkpointing | FireWorks |
| Batch parameter sweeps (thousands of independent runs) | RADICAL-Pilot |

FireWorks shines in structured materials science pipelines with well-defined task hierarchies. Parsl is best for exploratory, interactive scientific computing where the workflow evolves during the research process. RADICAL-Pilot excels at extreme-scale ensemble computing where resource acquisition efficiency is critical.

## Scaling Characteristics and Fault Tolerance Patterns

Each orchestrator handles scaling and failure recovery differently, reflecting their design philosophies for different classes of scientific workloads:

FireWorks scales through multiple Rocket launchers polling the shared MongoDB launchpad. In production at the Materials Project, 50+ concurrent Rockets process 100,000+ Fireworks across distributed computing resources. The centralized MongoDB database provides a single source of truth for workflow state, but becomes the scaling bottleneck above 500 concurrent launchers. For extreme-scale workflows, deploy MongoDB with sharding and configure Rockets to use categorized queries for work stealing across heterogeneous resources.

Parsl's DataFlow Kernel manages task scheduling in-memory within the submitting Python process. This provides sub-millisecond task dispatch latency — ideal for interactive workloads with short-duration tasks. For production deployments spanning thousands of cores, Parsl's HighThroughputExecutor uses a hub-worker model where the interchange process manages task distribution across worker nodes. The theoretical limit is approximately 10,000 concurrent tasks per executor instance, limited by the Python GIL in the interchange process.

RADICAL-Pilot's pilot-job model supports the highest task throughput — demonstrated at 10+ million tasks across 100,000+ cores on ORNL's Summit supercomputer. The pilot abstraction acquires resources once and multiplexes tasks within the allocation, eliminating per-task scheduler overhead. This is the most efficient approach for embarrassingly parallel ensemble computations where individual tasks run for seconds to minutes rather than hours.

For fault tolerance, all three provide automatic retry mechanisms. FireWorks detects stalled Fireworks via heartbeat monitoring and resubmits them. Parsl provides configurable retry with exponential backoff through Python decorators. RADICAL-Pilot handles pilot-level failures by reacquiring resources and rescheduling affected tasks onto the new pilot allocation. For workflows spanning multiple days or weeks, periodic database backups (FireWorks MongoDB dump, Parsl checkpoint files) are essential for disaster recovery.


## FAQ

### Can I use these tools on a single workstation without a cluster?

Yes. All three support local execution modes. Parsl's `ThreadPoolExecutor` and RADICAL-Pilot's `local.localhost` resource configuration work directly on laptops and workstations for development and testing.

### How do these compare to general workflow tools like Airflow or Prefect?

Scientific orchestrators provide native HPC scheduler integration (Slurm, PBS, LSF), dynamic workflow generation based on intermediate results, and high-throughput task management optimized for millions of short-duration compute tasks. General tools like Airflow are designed for scheduled data pipelines, not adaptive scientific computing.

### Does FireWorks require MongoDB administration?

Yes, FireWorks uses MongoDB as its workflow database. For small deployments, a single MongoDB instance is sufficient. For production, deploy a replica set for high availability. The web GUI connects directly to MongoDB for workflow visualization.

### Can Parsl workflows span multiple HPC clusters?

Yes. Parsl supports multi-site execution where different tasks run on different clusters simultaneously. This is configured through the `MultiProvider` and separate executor blocks in the Parsl config, though setting up cross-site authentication and data movement requires additional infrastructure.

### What happens when a task fails mid-execution?

FireWorks automatically detects task failures and re-runs the failed Firetask (configurable retry count). Parsl provides exception handling through Python's native try/except with retry decorators. RADICAL-Pilot detects failed tasks at the pilot level and can reschedule them onto available resources automatically.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted HPC Scientific Workflow Orchestrators: FireWorks vs Parsl vs RADICAL-Pilot Compared 2026",
  "description": "Comprehensive comparison of three open-source HPC scientific workflow orchestrators: FireWorks (424+ stars), Parsl (616+ stars), and RADICAL-Pilot (64+ stars). Includes installation guides, code examples, and use case recommendations.",
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
