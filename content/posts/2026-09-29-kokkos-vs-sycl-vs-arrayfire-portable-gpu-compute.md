---
title: "Kokkos vs SYCL vs ArrayFire in 2026: Portable GPU Compute Without Vendor Lock-In"
date: "2026-09-29"
tags: ["gpu", "hpc", "cpp", "performance", "scientific-computing"]
cover: "/img/screenshots/kokkos-portable-compute.jpg"
draft: false
---

Write a solver against CUDA today and you have made a hardware bet you cannot easily unwind: the next cluster you get access to may be AMD, the workstation refresh may be Intel, and the accelerator you actually want is whatever the grant or the cloud invoice allows this year. Vendor lock-in in HPC is not an abstract licensing concern — it is a rewrite measured in months of engineering. Kokkos, SYCL (via AdaptiveCpp) and ArrayFire attack the problem from three different directions: a performance-portability programming model, an open standard with a vendor-independent compiler, and a high-level array API with runtime kernel generation.

This comparison looks at what each one actually costs you in code, build complexity and peak performance, with **GitHub statistics collected on September 29, 2026**.

## TL;DR: The Quick Verdict

**Pick Kokkos** if you are writing HPC simulation code — particles, PDE solvers, molecular dynamics — and you want a single C++ source tree that compiles for NVIDIA, AMD, Intel and CPU backends with `parallel_for`/`parallel_reduce` abstractions. **Pick SYCL via AdaptiveCpp** if you want to stay inside an open standard, need to mix in existing CUDA or HIP code, or want one binary that adapts to whatever hardware it finds at runtime. **Pick ArrayFire** if you want the fastest path from an algorithm to working accelerator code, are happy with a higher-level array/tensor API, and value built-in image-processing, computer-vision and linear-algebra primitives.

Short version: **Kokkos for portable simulation kernels, SYCL for standardised heterogeneous C++, ArrayFire for rapid array-heavy prototyping.**

## Kokkos vs SYCL (AdaptiveCpp) vs ArrayFire at a Glance

| Dimension | Kokkos | SYCL / AdaptiveCpp | ArrayFire |
|---|---|---|---|
| GitHub stars | **2,688** | **1,946** | **4,904** |
| Last commit | 2026-09-28 | 2026-09-25 | 2026-09-12 |
| Licence | Apache-2.0 with LLVM Exceptions | BSD-style permissive | BSD-3-Clause |
| Programming model | C++ performance portability layer | Open standard (SYCL 2020) | High-level array API |
| Backends | CUDA, HIP, SYCL, OpenMP, HPX, C++ threads | CUDA, ROCm, CPU, (multi-vendor single binary) | CUDA, oneAPI, OpenCL, native CPU |
| Compilation model | Ahead-of-time, per backend | JIT by default, AOT optional | JIT kernel generation at runtime |
| Languages | C++17+ | C++17+ | C++, Python, Rust bindings |
| Repo | `Kokkos/kokkos` | `AdaptiveCpp/AdaptiveCpp` | `arrayfire/arrayfire` |
| Governance | Linux Foundation project | Community-driven | Company-backed with open source |

## Decision Matrix: Pick in 10 Seconds

| Your situation | Recommended | Why |
|---|---|---|
| Porting a large HPC simulation to a new accelerator | **Kokkos** | Views plus `parallel_for` map cleanly onto existing loop nests |
| Must support NVIDIA and AMD from one source tree | **Kokkos** or **AdaptiveCpp** | Kokkos switches backend at build time; AdaptiveCpp can target all vendors at once |
| Want an open standard rather than a framework | **SYCL / AdaptiveCpp** | SYCL is a Khronos standard; the compiler is independent of the hardware vendor |
| Image processing, signal processing, computer vision primitives | **ArrayFire** | Ships ready-made kernels for these domains |
| Existing CUDA code you cannot discard | **AdaptiveCpp** | Its portable CUDA dialect lets a single binary offload to multiple vendors |
| Fastest prototype from maths to working accelerator code | **ArrayFire** | Array expressions replace hand-written kernels |
| Running on an HPC cluster with module-provided builds | **Kokkos** | Widely packaged, including via Spack |
| Python-heavy team | **ArrayFire** (Python bindings) | `arrayfire-python` gives the same array model from Python |

## Kokkos — Performance Portability for Simulation Code (2,688 stars)

Kokkos provides two abstractions that carry almost all real workloads: **Views** for data and **parallel execution patterns** for loops. Node-level parallelism is expressed once, and the backend is chosen at build time — CUDA, HIP, SYCL, OpenMP, HPX or C++ threads. It is an Apache-2.0 project with LLVM Exceptions, governed by the Linux Foundation, which matters if you need to ship code into an institution with procurement rules.

The most reliable install path on HPC systems is Spack, which the project's README recommends:

```bash
spack install kokkos
spack info kokkos          # list all available configuration options
```

A typical from-source build selects the backend explicitly:

```bash
git clone https://github.com/kokkos/kokkos.git
cmake -B build -S kokkos \
  -DKokkos_ENABLE_OPENMP=ON \
  -DKokkos_ENABLE_CUDA=ON \
  -DKokkos_ENABLE_CUDA_LAMBDA=ON
cmake --build build -j
sudo cmake --install build
```

A complete portable kernel is short enough to read in one screen:

```cpp
#include <Kokkos_Core.hpp>

int main(int argc, char* argv[]) {
  Kokkos::initialize(argc, argv);
  {
    const int N = 1'000'000;
    Kokkos::View<double*> x("x", N);

    Kokkos::parallel_for("init", N, KOKKOS_LAMBDA(int i) {
      x(i) = 1.0;
    });

    double sum = 0.0;
    Kokkos::parallel_reduce("sum", N,
      KOKKOS_LAMBDA(int i, double& acc) { acc += x(i); }, sum);

    Kokkos::printf("sum = %f\n", sum);
  }
  Kokkos::finalize();
}
```

The same source compiles for a CPU with OpenMP and for a GPU with CUDA or HIP. **Where Kokkos wins:** minimal disruption when porting loop-heavy code, mature tooling (`Kokkos::Timer`, profiling hooks), institutional governance, and a decade of large-scale production use. **Where it hurts:** you restructure data into `View`s and rewrite iteration as patterns, the backend is fixed at compile time, and achieving peak performance still requires architecture-aware choices such as memory layout, team-level parallelism and vectorisation.

## SYCL via AdaptiveCpp — An Open Standard With an Independent Compiler (1,946 stars)

SYCL is a Khronos standard for C++ heterogeneous programming; AdaptiveCpp (formerly hipSYCL) is the community implementation that compiles for CPUs plus NVIDIA, AMD, Intel and Apple GPUs. Its distinguishing feature is a **JIT compiler based on LLVM** that is the default flow: the same binary can discover and use whatever hardware is present, including hardware from multiple vendors at once. There is also a portable CUDA dialect, so existing CUDA or HIP sources can be compiled into a single multi-vendor binary. It is distributed under a BSD-style permissive licence.

Building from source with the common backends enabled:

```bash
git clone https://github.com/AdaptiveCpp/AdaptiveCpp.git
cd AdaptiveCpp && mkdir build && cd build

cmake -DCMAKE_INSTALL_PREFIX=/opt/adaptivecpp \
      -DWITH_CUDA_BACKEND=ON \
      -DWITH_ROCM_BACKEND=ON \
      -DWITH_CPU_BACKEND=ON ..
make install
```

Compilation then looks like a normal compiler invocation, which is the point — the language is portable C++ plus standard extensions:

```bash
acpp -O2 -o vector_add vector_add.cpp
./vector_add
```

A standard SYCL kernel:

```cpp
#include <sycl/sycl.hpp>
#include <vector>

int main() {
  const int N = 1024;
  std::vector<float> a(N, 1.0f), b(N, 2.0f), c(N);

  sycl::queue q{sycl::default_selector_v};

  {
    sycl::buffer<float, 1> bufA(a.data(), N);
    sycl::buffer<float, 1> bufB(b.data(), N);
    sycl::buffer<float, 1> bufC(c.data(), N);

    q.submit([&](sycl::handler& h) {
      sycl::accessor accA(bufA, h, sycl::read_only);
      sycl::accessor accB(bufB, h, sycl::read_only);
      sycl::accessor accC(bufC, h, sycl::write_only);

      h.parallel_for(N, [=](sycl::id<1> i) {
        accC[i] = accA[i] + accB[i];
      });
    });
  }   // buffers flush back to host here

  return 0;
}
```

**Where AdaptiveCpp wins:** standardisation (your code is SYCL, not one project's dialect), a single binary across vendors, interoperability with existing CUDA/HIP sources, and a single-pass compilation model that keeps build times sane. **Where it hurts:** SYCL requires learning the queue/buffer/accessor model, the default JIT flow means runtime kernel compilation and cache management in production, and debugging a kernel on a machine without the target accelerator needs planning.

## ArrayFire — High-Level Arrays With Runtime Kernel Generation (4,904 stars)

ArrayFire is the pragmatic choice: instead of writing kernels, you write array expressions, and ArrayFire generates and fuses kernels for the device at hand — CUDA, oneAPI, OpenCL or native CPU. It is BSD-3-Clause licensed and ships hundreds of functions across linear algebra, statistics, signal processing and image processing, with the `af::array` type as the single data abstraction. The company-backed model also means commercial support exists if you need it.

Install through vcpkg, a package manager, or the official installers:

```bash
vcpkg install arrayfire
# or, for the Python bindings
pip install arrayfire
```

The README's own Conway's Game of Life example shows the style — array expressions, not loops:

```cpp
static const float h_kernel[] = { 1, 1, 1, 1, 0, 1, 1, 1, 1 };
static const af::array kernel(3, 3, h_kernel, afHost);

af::array state = (af::randu(128, 128, f32) > 0.5).as(f32);

// Neighbour count via convolution, then apply the rules as array maths
af::array nHood = af::convolve(state, kernel);
af::array next = (nHood == 2 && state) || (nHood == 3);

af::print("state", af::sum(next));
```

Because kernels are generated lazily, consecutive operations can be fused into fewer launches — a real benefit when your workload is a long chain of element-wise operations rather than one hand-tuned kernel.

**Where ArrayFire wins:** the shortest distance from an algorithm to accelerator code, domain primitives that would take days to write, multiple language bindings, and permissive BSD licensing. **Where it hurts:** you give up fine control over memory layout and launch configuration, the abstraction can be slower than a hand-written kernel for irregular workloads, JIT compilation has a warm-up cost, and the ecosystem is smaller than the CUDA-first tooling you may already know.

## Common Pitfalls When Building Portable Accelerator Code

- **Portability has a price at the top end.** A portable kernel typically lands within a few percent of a hand-tuned one for regular workloads, but irregular access patterns, warp-level primitives and vendor-specific instructions are where the gap widens. Benchmark before you assume.
- **Compile-time vs runtime backend selection changes your release process.** Kokkos fixes the backend when you build, so you ship one binary per accelerator family. AdaptiveCpp's JIT default ships one binary but pays a compile step on first run, and you need a writable cache directory — a genuine issue on locked-down clusters.
- **One GPU is not a portability test.** Verifying on an NVIDIA card proves your code compiles, not that it is portable. Test the CPU backend too: it catches memory-model mistakes and races that a GPU run can hide.
- **Memory space mistakes are the classic port.** Kokkos `View`s carry a memory space; mixing host and device pointers, or capturing a raw pointer in a device lambda, produces crashes that look random. Keep everything inside `View`s until it works, then optimise.
- **JIT warm-up distorts benchmarks.** Time steady-state iterations, not the first launch, or you will conclude the library is slow when it is compiling.
- **Pin your toolchain.** These projects track LLVM and compiler releases closely. `acpp` and Kokkos builds are sensitive to compiler versions; pin them in your build system the way you pin any dependency.
- **Profiling changes.** Vendor profilers only see the generated kernels. Kokkos and SYCL both emit tool-interface markers, but you must enable them at build time to get usable timelines.
- **Python bindings lag the C++ API.** ArrayFire's Python bindings and similar wrappers are convenient, but version alignment with the C++ core is worth checking before you build a pipeline on them.

For related reading, see our comparison of [Rust GPU abstraction layers including wgpu, Vulkano and Ash](../2026-09-28-rust-gpu-abstraction-wgpu-vulkano-ash-comparison/), our guide to [managing GPUs on Kubernetes with the NVIDIA Operator and Container Toolkit](../2026-05-04-self-hosted-gpu-management-kubernetes-nvidia-operator-container-toolkit-volcano/), and our rundown of [sparse linear solvers from SuiteSparse, MUMPS, PETSc, hypre and SuperLU](../2026-06-22-sparse-linear-solvers-suitesparse-mumps-petsc-hypre-superlu/).

## FAQ

**What is the difference between Kokkos and SYCL?**
Kokkos is a C++ library and programming model that abstracts parallel execution and data management, with the backend chosen at build time. SYCL is an open Khronos standard for heterogeneous C++ that a compiler implements; AdaptiveCpp is one such compiler, and it can target multiple vendors in a single binary. Kokkos can itself use SYCL as a backend.

**Can one binary really run on NVIDIA, AMD and Intel GPUs?**
With AdaptiveCpp, yes — its LLVM JIT flow is designed for that, including using hardware from several vendors in the same process. Kokkos builds a backend-specific binary, so you compile once per accelerator family. ArrayFire selects a runtime backend from whichever one you installed.

**Which is fastest?**
For regular array-heavy workloads, ArrayFire's fused kernels are competitive and dramatically faster than unoptimised code. For simulation kernels with irregular access, a tuned Kokkos kernel is usually within a few percent of hand-written CUDA or HIP. Neither claim survives without measurement on your own workload — benchmark before choosing.

**Do I need a GPU to develop with these?**
No. Kokkos has OpenMP, C++ threads and HPX backends; ArrayFire has a native CPU backend; AdaptiveCpp has a CPU backend and even offers accelerated CPU support. Developing against the CPU backend and running the same code on an accelerator is the standard workflow.

**Is ArrayFire still actively maintained?**
Yes — the repository shows commits in September 2026 and thousands of stars accumulated over a decade of use. The project is company-backed, so it follows a different model from the community-governed Kokkos effort, and commercial support is available.

**Which should I choose for a new HPC simulation project?**
Start with Kokkos if your workload is loop-based numerical simulation in C++ and your institution provides module or Spack builds. Choose SYCL via AdaptiveCpp when you need a standardised model, multiple vendors in one binary, or interoperability with existing CUDA and HIP code. Choose ArrayFire when the workload maps to array operations and you want results quickly.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Kokkos vs SYCL vs ArrayFire in 2026: Portable GPU Compute Without Vendor Lock-In",
  "description": "A practical 2026 comparison of Kokkos, SYCL via AdaptiveCpp and ArrayFire for portable GPU computing: backends, compilation models, licensing, code examples and portability pitfalls.",
  "datePublished": "2026-09-29",
  "dateModified": "2026-09-29",
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
