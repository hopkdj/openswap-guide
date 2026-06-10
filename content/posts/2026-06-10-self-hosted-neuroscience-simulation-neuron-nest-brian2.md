---
title: "Self-Hosted Neuroscience Simulation: NEURON vs NEST vs Brian2 Compared"
date: "2026-06-10"
tags: ["neuroscience", "simulation", "scientific-computing", "computational-biology", "hpc", "open-science"]
draft: false
---

## Introduction

Understanding how the brain computes requires simulating neuronal networks at multiple scales—from individual ion channels in a single dendrite to populations of thousands of interconnected neurons. Three open-source simulators have become the standard tools for computational neuroscience: **NEURON** (biophysically detailed single-neuron models), **NEST** (large-scale point-neuron networks), and **Brian2** (rapid prototyping with mathematical clarity).

Each simulator solves different problems along the neuroscience modeling spectrum, and many research labs self-host all three on institutional HPC clusters. This article compares their architectures, deployment strategies, and optimal use cases for self-hosted environments.

## Feature Comparison

| Feature | NEURON | NEST | Brian2 |
|---------|--------|------|--------|
| **Primary Domain** | Detailed neuron models (Hodgkin-Huxley type) | Large-scale spiking neural networks | Rapid prototyping and teaching |
| **GitHub Stars** | 523+ | 649+ | 1,189+ |
| **Current Version** | 9.0 | 3.8 | 2.7 |
| **Simulation Scale** | 1 to 10,000 neurons (compartmental) | 1,000 to 100 million neurons (point models) | 1 to 100,000 neurons (flexible) |
| **Model Specification** | NMODL / HOC / Python | SLI / PyNEST (Python) | Pure Python equations |
| **Neuron Models** | Hodgkin-Huxley, multi-compartment, extracellular | Integrate-and-fire, AdEx, HH (point) | Any equation-based model |
| **Parallelism** | MPI plus multi-threaded | MPI (hybrid parallel) | C++ code generation plus OpenMP |
| **Synaptic Plasticity** | Custom NMODL mechanisms | Built-in STDP, multiple variants | Equation-based (any plasticity rule) |
| **Gap Junctions** | Full support | Limited (gap-junction framework) | Equation-based |
| **GPU Support** | CoreNEURON backend (NVIDIA) | In development | Via C++ standalone mode (limited) |
| **Learning Curve** | Steep (NMODL, HOC language) | Moderate (PyNEST API) | Gentle (pure Python) |
| **License** | BSD 3-Clause | GPLv2 | CeCILL-2.1 |

## Self-Hosted Deployment

All three simulators are deployable via Docker for reproducible research environments. The following configuration sets up a JupyterHub server with all three simulators pre-installed:

```yaml
# docker-compose.yml — Neuroscience Simulation Stack
version: '3.8'
services:
  neuro-jupyter:
    image: jupyter/scipy-notebook:latest
    command:
      - bash
      - -c
      - "conda install -y -c conda-forge neuron nest-simulator brian2 && start-notebook.sh --NotebookApp.token=''"
    ports:
      - "8888:8888"
    volumes:
      - ./notebooks:/home/jovyan/work
      - ./data:/home/jovyan/data
      - ./models:/home/jovyan/models
    environment:
      - OMP_NUM_THREADS=4
      - NEST_NUM_THREADS=4
    deploy:
      resources:
        limits:
          cpus: '8'
          memory: 32G

  neuron-headless:
    image: neuronsimulator/nrn:latest
    volumes:
      - ./models:/models
      - ./results:/results
    entrypoint: ["nrniv", "-mpi", "-python"]
```

For HPC cluster installations, compile from source with MPI support to maximize parallel performance:

```bash
# NEURON compilation with Python and MPI support
git clone https://github.com/neuronsimulator/nrn.git
cd nrn && mkdir build && cd build
cmake .. \
  -DNRN_ENABLE_PYTHON=ON \
  -DNRN_ENABLE_MPI=ON \
  -DNRN_ENABLE_CORENEURON=ON \
  -DCMAKE_INSTALL_PREFIX=/opt/neuron
make -j$(nproc) && make install

# NEST installation with Python bindings
pip install nest-simulator

# Brian2 is pure pip install — no compilation needed
pip install brian2
```

### NEURON: Biophysically Detailed Models

NEURON excels at simulating neurons with detailed morphology—dendritic trees, dendritic spines, and spatially distributed voltage-gated ion channels. Its cable equation solver accounts for axial resistance along dendrites and membrane capacitance, producing quantitatively accurate predictions of synaptic integration at the subcellular level:

```python
from neuron import h, gui
from neuron.units import ms, mV

# Create a simplified pyramidal cell with soma and apical dendrite
soma = h.Section(name='soma')
dend = h.Section(name='dend')

# Set dimensions: soma 20um diameter, dendrite 200um long and 3um diameter
soma.L = 20
soma.diam = 20
dend.L = 200
dend.diam = 3
dend.connect(soma, 1, 0)

# Insert Hodgkin-Huxley sodium and potassium channels in soma
soma.insert('hh')
for seg in soma:
    seg.hh.gnabar = 0.12  # Sodium conductance (S/cm2)
    seg.hh.gkbar = 0.036  # Potassium conductance (S/cm2)

# Insert passive leak channels in dendrite
dend.insert('pas')
for seg in dend:
    seg.pas.g = 0.001   # Leak conductance (S/cm2)
    seg.pas.e = -65 * mV  # Reversal potential

print(f"Model ready: {soma.nseg + dend.nseg} compartments total")
```

### NEST: Large-Scale Spiking Networks

NEST handles networks with millions of integrate-and-fire neurons connected by plastic synapses. Its hybrid parallelization uses MPI across compute nodes and threads within nodes, scaling efficiently to supercomputing-scale simulations with billions of synapses:

```python
import nest

# Initialize NEST kernel with hybrid parallelism
nest.ResetKernel()
nest.SetKernelStatus({
    'local_num_threads': 4,
    'total_num_virtual_procs': 4
})

# Create balanced random network with 80% excitatory, 20% inhibitory
exc_neurons = nest.Create('iaf_psc_alpha', 8000)
inh_neurons = nest.Create('iaf_psc_alpha', 2000)

# Configure neuron parameters
nest.SetStatus(exc_neurons, {
    'V_m': -70.0,
    'tau_syn_ex': 0.5,
    'E_L': -70.0,
    'C_m': 250.0
})
nest.SetStatus(inh_neurons, {
    'V_m': -70.0,
    'tau_syn_in': 1.0,
    'E_L': -70.0,
    'C_m': 250.0
})

# Connect populations with fixed indegree
nest.Connect(exc_neurons, exc_neurons,
             {'rule': 'fixed_indegree', 'indegree': 1000},
             {'weight': 0.1, 'delay': 1.5})

nest.Connect(exc_neurons, inh_neurons,
             {'rule': 'fixed_indegree', 'indegree': 1000},
             {'weight': 0.1, 'delay': 1.5})

# Simulate 1000 ms of network activity
nest.Simulate(1000.0)
print(f"Simulated {nest.GetKernelStatus()['network_size']} neurons for 1 second")
```

### Brian2: Rapid Prototyping with Mathematical Notation

Brian2 translates neuron model equations directly from mathematical notation into efficient simulation code. This makes it ideal for exploring new models and teaching computational neuroscience—students write the same equations from their textbooks:

```python
from brian2 import *

# Define integrate-and-fire neuron with exponential synapse
# Uses mathematical notation directly matching textbook equations
eqs = '''
dv/dt = (g_l*(E_l-v) + g_e*(E_e-v) + I_stim) / C_m : volt
dg_e/dt = -g_e / tau_e : siemens
I_stim = stimulus(t, i) : amp
'''

# Create neuron group with 100 neurons
G = NeuronGroup(100, eqs,
                threshold='v > -50*mV',
                reset='v = -70*mV',
                method='euler')

# Initialize membrane potentials
G.v = -70 * mV
G.g_e = 0 * nS

# Connect with sparse random synapses
S = Synapses(G, G, 'w : siemens', on_pre='g_e += w')
S.connect(p=0.1)
S.w = '0.5*nS + 0.2*nS*rand()'

# Run simulation for 1 second
run(1000 * ms)
print(f"Simulation complete: {G.N} neurons")
```

## Performance and Scaling Considerations

Neuroscience simulations span an enormous range of computational demands—from a single-compartment model running in milliseconds on a laptop to a full-scale cortical microcircuit requiring hours on a supercomputer. Understanding the performance characteristics of each simulator is essential for planning self-hosted deployments.

**NEURON** achieves its best performance through CoreNEURON, its GPU-accelerated backend. On a single NVIDIA A100, CoreNEURON can simulate a 10,000-compartment neuron model 20-40x faster than CPU-only execution. For networks of detailed neurons, MPI-based parallelization distributes cells across nodes, with each node handling the computationally expensive cable equation integration. Typical throughput for a 32-core node running network simulations with 500 detailed pyramidal cells is approximately 100-200 seconds of biological time per wall-clock hour.

**NEST** employs a fundamentally different parallelization strategy optimized for point-neuron networks. Its distributed spike exchange algorithm uses MPI collective operations with minimal communication overhead—each MPI process only receives spikes from neurons targeting its local population. This enables weak scaling to 10,000+ MPI processes on Tier-1 supercomputers. For local institutional clusters, NEST achieves near-linear speedup up to approximately 128 cores for networks of 100,000+ neurons with dense connectivity. Memory usage is dominated by synapse storage, approximately 40 bytes per synapse in the default data structure.

**Brian2** generates C++ code at runtime for computational efficiency while maintaining Python-level model specification. For spiking neural networks, Brian2's code generation produces vectorized loops that achieve 80-95% of hand-written C++ performance without any user compilation steps. The "standalone" mode generates complete C++ projects that compile independently of Python, enabling deployment on systems without Python installations—useful for embedded neuromorphic hardware testing. For typical network models of 10,000 neurons with conductance-based synapses, Brian2 in C++ standalone mode processes approximately 500 seconds of biological time per wall-clock minute on a modern 16-core workstation.

## Why Self-Host Your Neuroscience Simulators?

Self-hosting neuroscience simulation infrastructure provides reproducibility guarantees that cloud platforms cannot match. When a reviewer asks you to re-run a simulation from your 2024 paper, having the exact same software stack—down to the compiler version and MPI library patch level—is essential for producing identical numerical results. Docker containers and environment modules on institutional clusters preserve this bit-level reproducibility across years, while cloud platforms continuously update their base images.

Cost is the dominant factor for large-scale simulations. A single simulation of a cortical microcircuit model in NEST using 1,000 MPI processes for 48 hours consumes approximately 48,000 core-hours. On AWS (c5.18xlarge at approximately $3.06 per hour for 72 vCPUs), this costs roughly $2,450. On an institutional cluster with amortized hardware costs, the same simulation costs $200-400. For labs running multiple large-scale simulations weekly, the savings from self-hosted HPC infrastructure exceed $100,000 annually.

Privacy concerns also drive self-hosting decisions in neuroscience. Computational models of neurological disorders often involve data derived from patient MRI and EEG recordings. Many institutional review boards (IRBs) require these derivative datasets to remain on institutional servers. Self-hosted simulation servers satisfy IRB data governance requirements while enabling the interactive, iterative workflow that computational neuroscience demands for model tuning.

Teaching laboratories benefit enormously from self-hosted Brian2 instances. Instead of troubleshooting student laptop installations across Windows, macOS, and Linux, instructors deploy a single JupyterHub server with pre-configured Python environments. Students access identical notebook-based coursework through their browsers, ensuring every tutorial cell produces the expected output regardless of the student's local machine. For course enrollment of 100+ students, a single 32-core server handles concurrent simulation workloads without queuing delays during laboratory sessions.

For comparison with other scientific simulation tools, see our [computational chemistry engines guide](../2026-06-10-self-hosted-computational-chemistry-engines-pyscf-psi4-nwchem/) covering PySCF, Psi4, and NWChem. For HPC container runtime options, our [HPC container runtimes comparison](../2026-06-01-self-hosted-hpc-container-runtimes-apptainer-charliecloud-podman-hpc-guide/) covers Apptainer, Charliecloud, and Podman-HPC. For general scientific simulation context, our [OpenFOAM vs Elmer vs CalculiX guide](../2026-06-08-self-hosted-scientific-simulation-openfoam-elmer-calculix/) covers engineering simulation tools.

## FAQ

### Which simulator should I learn first as a computational neuroscience student?

Start with **Brian2**. Its equation-based modeling syntax directly mirrors the mathematical descriptions in textbooks and research papers, making it the most intuitive for learning. You can extract the differential equations from any neuroscience paper and type them directly into Brian2 without translation. Once you understand the underlying concepts, transition to NEURON for morphologically detailed models or NEST for large-scale network simulations. Many labs use Brian2 for prototyping and NEST for production-scale runs.

### Can I mix these simulators in the same research project?

Yes, and many labs do exactly this. A common workflow uses Brian2 for initial model exploration and rapid parameter sweeps, then ports the validated model to NEURON for detailed dendritic integration studies, or to NEST for large-scale population-level predictions. PyNN (Python Neural Networks) provides a unified API across simulators, allowing you to write a model once and run it on NEURON, NEST, or Brian2 backends by changing a single import statement. This multi-simulator approach also serves as cross-validation—comparing results across simulators builds confidence in your findings.

### How do I deploy these on a Kubernetes cluster?

Package each simulator as a separate Docker container and deploy via Kubernetes Jobs for batch simulations or via JupyterHub for interactive work. Use PersistentVolumeClaims for shared model storage and results directories. For MPI-based simulators (NEURON, NEST), use the MPI Operator for Kubernetes to manage multi-pod parallel execution with proper network fabric configuration. Each MPI process in a NEST simulation can run in its own pod with dedicated CPU allocation, enabling clean resource isolation between users on a shared cluster.

### What is the minimum hardware for a small computational neuroscience lab?

A single server with 32 CPU cores, 128 GB RAM, and 500 GB NVMe SSD supports a 5-10 person lab comfortably. For NEURON models with complex morphologies, allocate at minimum 4 GB RAM per detailed neuron model with thousands of compartments. NEST simulations of 100,000+ neurons with plastic synapses require 32-64 GB RAM primarily for synapse storage. Brian2's code generation produces memory-efficient binaries that typically use 25-50% less RAM than interpreted Python simulation loops. Budget approximately $8,000-12,000 for a capable single-server deployment.

### Are there alternatives to these three simulators?

Yes, several alternatives exist for specific use cases. **Arbor** is a newer simulator from the Human Brain Project focusing on GPU-accelerated detailed neuron models with a modern C++ architecture. **GeNN** (GPU-enhanced Neural Networks) targets GPU execution specifically and achieves excellent performance for integrate-and-fire networks. **The Virtual Brain** focuses on whole-brain simulation at the mesoscopic scale using neural mass models rather than spiking neurons. **GENESIS** is the historical predecessor to NEURON and is still used in some established labs. However, NEURON, NEST, and Brian2 remain the most widely documented and community-supported options for most computational neuroscience research needs.

### How do I handle long-running simulations that take days or weeks?

For multi-day simulations, use checkpointing to save intermediate states. NEURON supports save/restore of full simulation state via its `finitialize` and `finitialize` functions. NEST provides `GetStatus` and `SetStatus` for checkpointing network states. Brian2's `store` and `restore` methods save complete network states to disk. Combine these with your cluster's job scheduler to implement automatic restarts: if a node fails mid-simulation, the scheduler restarts the job from the most recent checkpoint rather than from the beginning. For simulations exceeding your cluster's maximum walltime, implement periodic checkpointing every 4-6 hours and chain multiple job submissions.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Neuroscience Simulation: NEURON vs NEST vs Brian2 Compared",
  "description": "Comprehensive comparison of NEURON, NEST, and Brian2 for self-hosted computational neuroscience simulation. Learn deployment with Docker Compose, MPI parallelization, and choose the right simulator for your research.",
  "datePublished": "2026-06-10",
  "dateModified": "2026-06-10",
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
