---
title: "Self-Hosted Quantum Computing Simulators: Qiskit vs Cirq vs ProjectQ"
date: "2026-06-09"
tags: ["quantum-computing", "simulation", "scientific-computing", "research", "python", "physics"]
draft: false
---

Quantum computing promises to solve problems that are intractable for classical computers — from drug discovery to materials science to cryptography. But real quantum hardware remains scarce and expensive, with access gated behind cloud providers like IBM Quantum and AWS Braket. Self-hosted quantum computing simulators let you develop and test quantum algorithms on your own infrastructure, without usage quotas or per-shot billing. In this comparison, we evaluate three leading open-source frameworks: **Qiskit** (IBM), **Cirq** (Google), and **ProjectQ** (ETH Zurich).

## Why Self-Host Your Quantum Simulator?

Cloud quantum services charge by the quantum circuit execution — with complex algorithms requiring thousands of shots for statistical significance, costs can escalate quickly during development. A self-hosted simulator running on your own GPU server or HPC cluster gives you unlimited execution, faster iteration cycles, and complete control over the simulation backend.

Beyond cost, self-hosting provides reproducibility benefits for research. You control the exact simulator version and configuration, ensuring that results from your papers can be replicated years later without worrying about cloud API deprecations. For organizations in regulated industries, local execution keeps sensitive algorithmic IP within your network perimeter.

For related scientific computing platforms, see our [guide to robotics simulation platforms](../2026-06-09-self-hosted-robotics-simulation-gazebo-webots-coppeliasim-guide/). If you need data versioning for research outputs, our [data versioning comparison](../apache-iceberg-vs-hudi-vs-delta-lake-open-data-lakehouse-formats-2026/) covers tools for managing large scientific datasets. For broader research infrastructure, our [electronic lab notebook guide](../2026-05-04-self-hosted-electronic-lab-notebook-elabftw-chemotion-labkey-guide/) explores platforms for managing experimental records.

## Comparison at a Glance

| Feature | Qiskit | Cirq | ProjectQ |
|---------|--------|------|----------|
| **GitHub Stars** | 7,463 | 4,982 | 976 |
| **Developer** | IBM | Google | ETH Zurich |
| **Language** | Python | Python | Python |
| **GPU Acceleration** | Yes (cuQuantum) | Yes (qsim) | Limited |
| **Noise Models** | Comprehensive | Comprehensive | Basic |
| **Quantum Hardware** | IBM Q backends | Google QCS | IBM, AQT, IonQ |
| **Circuit Visualization** | Rich (matplotlib, LaTeX) | Basic (text/SVG) | Built-in drawing |
| **Transpilation** | Advanced (multiple levels) | Built-in | Manual |
| **Community Size** | Largest | Large | Niche |
| **Latest Release** | Active (2026) | Active (2026) | Active (2026) |

## Qiskit: The Full-Stack Quantum SDK

Qiskit is IBM's open-source quantum computing framework and the most comprehensive option available. It covers the entire quantum computing workflow — from circuit construction and simulation to transpilation and execution on real quantum hardware.

**Key Strengths:**
- Rich transpiler with multiple optimization levels for circuit depth reduction
- Built-in noise models calibrated from real IBM Quantum hardware
- Qiskit Aer provides high-performance C++ simulation backends
- GPU acceleration via NVIDIA cuQuantum integration
- Extensive algorithm library (Qiskit Algorithms) with VQE, QAOA, Grover, Shor, and more

**Installation and Basic Usage:**

```bash
# Install Qiskit with visualization support
pip install qiskit qiskit-aer matplotlib pylatexenc

# Optional: GPU acceleration
pip install qiskit-aer-gpu
```

```python
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
import numpy as np

# Create a 3-qubit GHZ state circuit
qc = QuantumCircuit(3)
qc.h(0)
qc.cx(0, 1)
qc.cx(1, 2)
qc.measure_all()

# Run on the Aer simulator with a noise model
simulator = AerSimulator()
# Add realistic noise (T1/T2 decoherence, gate errors)
noise_model = None  # Use AerSimulator.from_backend() for real noise
result = simulator.run(qc, shots=1024).result()
counts = result.get_counts()
print(f"Measurement counts: {counts}")
# Expected: {'000': ~512, '111': ~512}
```

**Deployment on a Server:** Qiskit simulations run as standard Python processes. For multi-user access, deploy it behind JupyterHub:

```bash
pip install jupyterhub jupyterlab
jupyterhub --port 8000
```

## Cirq: Google's Quantum Framework

Cirq is Google's open-source framework for designing, simulating, and executing quantum circuits. It excels at fine-grained control over qubit placement and gate operations — essential for working with noisy intermediate-scale quantum (NISQ) devices.

**Key Strengths:**
- Device-aware circuit construction with topology constraints
- qsim: Google's high-performance C++ simulator with GPU support via CUDA
- Native integration with Google's Quantum Computing Service (QCS)
- Strong support for variational algorithms and quantum machine learning
- OpenFermion integration for quantum chemistry simulations

**Installation and Basic Usage:**

```bash
pip install cirq cirq-core
# Optional: GPU simulation
pip install qsimcirq
```

```python
import cirq
import numpy as np

# Create qubits on a grid (mimics hardware topology)
qubits = cirq.GridQubit.rect(2, 2)

# Build a circuit with device-aware placement
circuit = cirq.Circuit([
    cirq.H(qubits[0]),
    cirq.CNOT(qubits[0], qubits[1]),
    cirq.CNOT(qubits[0], qubits[2]),
    cirq.measure(*qubits, key='result')
])

# Simulate with noise
simulator = cirq.Simulator()
result = simulator.run(circuit, repetitions=1000)
print(result.histogram(key='result'))
```

## ProjectQ: ETH Zurich's Lightweight Framework

ProjectQ, developed at ETH Zurich, takes a different approach — it emphasizes a clean, Pythonic syntax and a powerful optimizing compiler that translates high-level quantum operations into low-level gates.

**Key Strengths:**
- High-level quantum programming constructs (quantum while loops, user-defined gates)
- Powerful compiler with resource estimation and circuit optimization
- Emulation backends for debugging quantum programs
- Smaller, more approachable codebase than Qiskit or Cirq
- Good educational tool due to clean API design

**Installation and Basic Usage:**

```bash
pip install projectq
```

```python
from projectq import MainEngine
from projectq.ops import H, CNOT, Measure, All

# Create quantum engine
eng = MainEngine()

# Allocate 3 qubits
qubits = eng.allocate_qureg(3)

# Build GHZ state
H | qubits[0]
CNOT | (qubits[0], qubits[1])
CNOT | (qubits[1], qubits[2])

# Measure
All(Measure) | qubits

# Flush and get results
eng.flush()
for i, q in enumerate(qubits):
    print(f"Qubit {i}: {int(q)}")
```

### Simulating at Scale

For large-scale simulations (20+ qubits), GPU acceleration is essential. Qiskit Aer with cuQuantum and Cirq with qsim both support GPU backends that can handle 30+ qubit simulations on a single NVIDIA A100 or H100 GPU. A dedicated simulation server with 2-4 GPUs and 64 GB RAM can simulate circuits up to approximately 36 qubits.

| Simulation Scale | Qubits | Memory Required | Recommended Hardware |
|-----------------|--------|-----------------|---------------------|
| Small | 10-20 | 4-8 GB | CPU, any modern server |
| Medium | 20-28 | 16-32 GB | Single GPU (A100) |
| Large | 28-34 | 64-256 GB | Multi-GPU (2-4x A100) |
| Full State | 35+ | 1 TB+ | HPC cluster with distributed memory |

For most research applications, the 20-30 qubit range covers the vast majority of algorithm development needs before moving to real quantum hardware.


### Integration with Your Research Pipeline

All three frameworks integrate well with scientific Python ecosystems. Qiskit works seamlessly with the IBM Quantum ecosystem and has the most extensive algorithm library — if you need VQE, QAOA, Grover's search, or Shor's algorithm out of the box, Qiskit provides them as high-level components. Cirq excels when you need fine-grained control over qubit placement and gate scheduling, making it the preferred choice for researchers working on near-term quantum error correction and noise mitigation. ProjectQ's clean API and optimizing compiler make it ideal for teaching and for projects where code readability matters as much as raw performance.

For teams running simulations on shared infrastructure, consider deploying JupyterHub with pre-configured kernels for each framework. This allows multiple researchers to share GPU resources efficiently while maintaining isolated Python environments. Combined with a network file system for result storage, this setup creates a collaborative quantum computing development environment that rivals cloud services in convenience while eliminating per-shot costs.

## FAQ

### Do I need a quantum computer to use these simulators?

No. All three frameworks include classical simulators that run on standard CPU or GPU hardware. They simulate the behavior of quantum circuits using linear algebra, allowing you to develop and test quantum algorithms without access to quantum hardware. When you are ready to run on real quantum devices, Qiskit connects to IBM Quantum and Cirq connects to Google QCS.

### What is the maximum number of qubits I can simulate?

On a standard server with 16 GB RAM, you can simulate approximately 25-28 qubits (state vector requires 2^n complex numbers). With GPU acceleration, 30-34 qubits is achievable on high-end hardware. Beyond that, you need to use tensor network or stabilizer simulation methods that trade generality for scale — specific algorithms like surface code simulations can reach 100+ qubits with these techniques.

### Which framework should a beginner choose?

Qiskit has the largest community, best documentation, and most tutorials. Its textbook (Qiskit Textbook) and learning platform provide an excellent on-ramp for newcomers. Start with Qiskit to learn the fundamentals, then explore Cirq if you need hardware-specific optimizations or ProjectQ if you value a clean, minimal API.

### Can I run hybrid quantum-classical algorithms locally?

Absolutely. Variational Quantum Eigensolver (VQE), Quantum Approximate Optimization Algorithm (QAOA), and quantum machine learning algorithms all involve classical optimization loops around quantum circuit evaluations. Self-hosted simulators are ideal for this workflow since each optimization step requires hundreds of circuit evaluations — doing this on cloud quantum services would be extremely slow and expensive.

### Are these simulators suitable for production workloads?

For algorithm research and development, yes. For production workloads that require actual quantum advantage, simulators have inherent limitations — the exponential growth of the state vector means classical simulation becomes infeasible as you scale beyond ~50 qubits. At that point, you transition to real quantum hardware. The simulators are best used for developing algorithms that can later run on NISQ devices.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Quantum Computing Simulators: Qiskit vs Cirq vs ProjectQ",
  "description": "Compare three open-source quantum computing simulation frameworks — IBM Qiskit, Google Cirq, and ETH Zurich ProjectQ — for self-hosted quantum algorithm development.",
  "datePublished": "2026-06-09",
  "dateModified": "2026-06-09",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💡 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
