---
title: "EJML vs Apache Commons Math vs ND4J in 2026: Which JVM Math Library Should You Actually Use?"
date: "2026-11-10"
tags: ["java", "jvm", "numerical-computing", "linear-algebra", "scientific-computing", "benchmarks"]
draft: false
cover: "/img/screenshots/jvm-math-commons.jpg"
description: "A practical 2026 comparison of EJML 0.46, Apache Commons Math 3.6.1 and ND4J 1.0.0-M2.1 — Maven coordinates, real code, a JMH benchmark harness, and the native-library traps that bite in production."
---

Multiply two 1,000 × 1,000 matrices on the JVM and the wall clock can differ by more than an order of magnitude depending on which library you imported — same JDK, same CPU, same heap. That gap is not a hardware problem. It is a data-layout and dispatch problem, and it is decided the moment you add a dependency to `pom.xml`. Three libraries cover most of the JVM's numerical work: **EJML** (616 stars, 0.46.1), **Apache Commons Math** (659 stars, 3.6.1 stable with 4.0 in beta), and **ND4J** (part of the Eclipse DeepLearning4j monorepo, 14,277 stars, 1.0.0-M2.1). They are not interchangeable, and picking the wrong one costs you either throughput or a 1 GB container image.

## TL;DR: The 30-Second Verdict

**Use EJML** for dense and sparse linear algebra where you want pure-Java speed, no native libraries, and a predictable 2 MB JAR. **Use Apache Commons Math** when the job is statistics, distributions, random generators, ODE solvers or optimization — its linear algebra is serviceable but not why you are there. **Use ND4J** when your arrays are tensors, your matrices are huge, or you need GPU/BLAS acceleration and can afford the native payload. If you only ever solve a 3 × 3 system, none of this matters — use whatever is already on the classpath.

## Side-by-Side Comparison

| Dimension | EJML | Apache Commons Math | ND4J |
|---|---|---|---|
| Stable version | **0.46.1** | **3.6.1** (4.0-beta1 in progress) | **1.0.0-M2.1** |
| GitHub stars | 616 | 659 | 14,277 (monorepo) |
| License | Apache-2.0 | Apache-2.0 | Apache-2.0 |
| Last commit | 2026-07-31 | 2026-11-09 | 2026-10-05 |
| Pure JVM | **Yes** | **Yes** | No — ships native backends |
| Native BLAS | Optional (via EJML fork) | No | **Yes** (OpenBLAS, MKL, CUDA) |
| GPU support | No | No | **Yes** (CUDA backend) |
| N-dimensional tensors | 2-D matrices (1-D vectors) | 2-D matrices | **0-D to N-D** |
| Sparse support | **Yes**, dedicated sparse solvers | Limited | Yes (sparse INDArray) |
| API style | Procedural (`CommonOps_DDRM.solve`) | Object-oriented (`RealMatrix`) | Tensor (`INDArray.mmul`) |
| Artifact size (runtime) | ~2 MB | ~2.2 MB | ~40 MB API + **~800 MB natives** |
| Best fit | Fast matrix math in-process | Statistics, optimization, ODEs | Large tensors, GPU, BLAS throughput |

## Decision Matrix: Pick in 10 Seconds

| Your situation | Recommended | Why |
|---|---|---|
| Solve linear systems, invert matrices, compute SVD inside a web service | **EJML** | Pure Java, no native crash surface, fastest single-threaded dense ops |
| Compute means, percentiles, t-tests, chi-square, bootstrap confidence intervals | **Apache Commons Math** | `DescriptiveStatistics` and the distribution package are the reason to add it |
| Fit a model with Levenberg-Marquardt or run a genetic algorithm | **Apache Commons Math** | Mature optimizers and ODE integrators, no native deps |
| Multiply matrices bigger than ~4,000 × 4,000 | **ND4J** | BLAS-backed, multi-threaded, orders of magnitude faster than pure Java at that size |
| Train or serve a tensor model on the JVM | **ND4J** | N-dimensional arrays, GPU backend, ecosystem integration |
| Ship a 60 MB container and keep it small | **EJML** | ND4J's natives alone dwarf your application |
| Need both statistics and fast matrix math | **Commons Math + EJML** | They coexist cleanly; use each for what it does best |

## EJML 0.46 — Pure Java, Procedural, Fast

Efficient Java Matrix Library is the library you reach for when you want matrix work to be a function call, not an object graph. It generates specialized code for double/single/real/complex and dense/sparse, so `CommonOps_DDRM` operates directly on primitive arrays with no boxing and no virtual dispatch per element.

```xml
<dependency>
  <groupId>org.ejml</groupId>
  <artifactId>ejml-all</artifactId>
  <version>0.46.1</version>
</dependency>
```

Solving a linear system — the canonical EJML workflow — is three lines and zero allocation surprises:

```java
import org.ejml.data.DMatrixRMaj;
import org.ejml.dense.row.CommonOps_DDRM;
import org.ejml.dense.row.factory.DecompositionFactory_DDRM;

DMatrixRMaj A = new DMatrixRMaj(new double[][]{
        {4, -2, 1},
        {-2, 4, -2},
        {1, -2, 4}
});
DMatrixRMaj b = new DMatrixRMaj(3, 1, true, 3, 6, 3);

DMatrixRMaj x = new DMatrixRMaj(3, 1);
CommonOps_DDRM.solve(A, b, x);       // LU-based solve, reuses internal workspace

double det = CommonOps_DDRM.det(A);
System.out.println("x = " + x);       // x = [1.0, 2.0, 3.0]
```

For decompositions you pick the algorithm explicitly instead of hoping the library guesses:

```java
var svd = DecompositionFactory_DDRM.svd(A.numRows, A.numCols, true, true, false);
svd.decompose(A);
double[] singularValues = svd.getSingularValues();
```

That explicitness is EJML's core design bet: you know whether memory was allocated, you know which decomposition ran, and you can pre-allocate workspaces for a hot loop. `EjmlParameters` and the `*_DDRM` variants exist precisely so a request handler can reuse buffers instead of allocating 1 MB per call.

**Where it hurts:** the API is verbose compared with NumPy-style code, sparse support is real but sparsely documented, and there is no statistics package — you get linear algebra, not a data-analysis toolkit.

## Apache Commons Math 3.6.1 — The Statistics Workhorse

Commons Math is not really a linear algebra library that happens to include statistics. It is a numerical toolkit where `RealMatrix` is one of a dozen subsystems: distributions, random generators, descriptive statistics, regression, interpolation, integration, ODE solvers, genetic algorithms and a Levenberg-Marquardt optimizer.

```xml
<dependency>
  <groupId>org.apache.commons</groupId>
  <artifactId>commons-math3</artifactId>
  <version>3.6.1</version>
</dependency>
```

Linear algebra uses an object-oriented `RealMatrix` API:

```java
import org.apache.commons.math3.linear.*;
import org.apache.commons.math3.stat.descriptive.DescriptiveStatistics;
import org.apache.commons.math3.distribution.TDistribution;

RealMatrix m = new Array2DRowRealMatrix(new double[][]{
        {4, -2, 1}, {-2, 4, -2}, {1, -2, 4}});
RealVector rhs = new ArrayRealVector(new double[]{3, 6, 3});

DecompositionSolver solver = new LUDecomposition(m).getSolver();
RealVector solution = solver.solve(rhs);          // [1, 2, 3]

DescriptiveStatistics stats = new DescriptiveStatistics();
double[] latencies = {12.1, 11.8, 41.3, 12.4, 12.0, 13.9};
for (double v : latencies) stats.addValue(v);

double p99 = stats.getPercentile(99);
double ci95 = new TDistribution(stats.getN() - 1).inverseCumulativeProbability(0.975)
              * stats.getStandardDeviation() / Math.sqrt(stats.getN());
```

![Cluster comparison plot generated by Apache Commons Math's k-means implementation](/img/screenshots/jvm-math-clustering.jpg "Commons Math ships real clustering and plotting examples — this chart is produced by its own KMeansPlusPlusClusterer")

The 4.0 line is in beta (`rel/commons-math-4.0-beta1` is tagged in the repository) and restructures packages, so treat 3.6.1 as the stable contract for now. Migration to 4.0 will be a package rename exercise, not an API rewrite — but it will touch imports across your codebase.

**Where it hurts:** every `RealMatrix` operation allocates, `Array2DRowRealMatrix` boxes into `double[][]`, and there is no workspace reuse. In a tight numerical loop this shows up immediately as GC pressure. Use it for statistics and optimization; delegate the inner matrix loop to EJML.

## ND4J 1.0.0-M2.1 — Tensors, BLAS and GPU

ND4J gives the JVM an `INDArray`: an N-dimensional, off-heap-capable tensor with pluggable backends. The API is the closest thing Java has to NumPy, and the backend is where the speed comes from — `nd4j-native` with OpenBLAS, or `nd4j-cuda` for GPU execution.

```xml
<dependency>
  <groupId>org.nd4j</groupId>
  <artifactId>nd4j-native-platform</artifactId>
  <version>1.0.0-M2.1</version>
</dependency>
```

```java
import org.nd4j.linalg.api.ndarray.INDArray;
import org.nd4j.linalg.factory.Nd4j;
import org.nd4j.linalg.ops.transforms.Transforms;

INDArray a = Nd4j.rand(2000, 2000);
INDArray b = Nd4j.rand(2000, 2000);

INDArray c = a.mmul(b);                        // BLAS sgemm, multi-threaded
INDArray t = Transforms.tanh(c);
double mean = c.meanNumber().doubleValue();

INDArray batch = Nd4j.create(new double[]{1, 2, 3, 4}, new int[]{2, 2});
System.out.println(batch.shapeInfoToString());  // rank 2, shape [2, 2]
```

The `-platform` artifact is a convenience POM that pulls native binaries for Linux, macOS and Windows. In a container you should depend on `nd4j-native` with the classifier you actually deploy, otherwise you ship three platforms' worth of shared objects:

```xml
<dependency>
  <groupId>org.nd4j</groupId>
  <artifactId>nd4j-native</artifactId>
  <version>1.0.0-M2.1</version>
  <classifier>linux-x86_64</classifier>
</dependency>
```

**Where it hurts:** native libraries mean native failures. `UnsatisfiedLinkError`, glibc mismatches on Alpine, and JVM crashes that produce `hs_err_pid` files instead of stack traces. Pin the classifier, use a glibc base image (not musl), and add `-Dorg.bytedeco.javacpp.maxphysicalbytes` limits if you run in a memory-capped container. Also expect ~800 MB of natives for the CUDA variant.

## Benchmark It Yourself (Do Not Trust Blog Numbers)

Published microbenchmarks age badly. The only number that matters is your workload on your hardware, and a naive `System.nanoTime()` loop will lie to you because the JIT has not compiled the hot path yet. Use JMH:

```java
@State(Scope.Thread)
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MILLISECONDS)
@Warmup(iterations = 5, time = 2)
@Measurement(iterations = 5, time = 3)
@Fork(2)
public class MatMulBench {

    @Param({"256", "1024", "2048"})
    int n;

    private DMatrixRMaj ejmlA, ejmlB, ejmlC;
    private INDArray nd4jA, nd4jB;

    @Setup
    public void setup() {
        double[] data = new double[n * n];
        new Random(42).nextDoubles(data);
        ejmlA = new DMatrixRMaj(n, n, true, data.clone());
        ejmlB = new DMatrixRMaj(n, n, true, data.clone());
        ejmlC = new DMatrixRMaj(n, n);
        nd4jA = Nd4j.create(data.clone(), new int[]{n, n});
        nd4jB = Nd4j.create(data.clone(), new int[]{n, n});
    }

    @Benchmark
    public void ejml() { CommonOps_DDRM.mult(ejmlA, ejmlB, ejmlC); }

    @Benchmark
    public void nd4j() { nd4jA.mmul(nd4jB); }
}
```

Run with `mvn clean package && java -jar target/benchmarks.jar`. Expect EJML to win at small and medium sizes single-threaded (no BLAS call overhead, no off-heap copies), and ND4J to pull ahead once matrices are large enough that BLAS threading pays for itself. EJML's own published benchmark suite compares against several JVM and native libraries and is worth reading for methodology; Commons Math is consistently the slowest of the three for raw multiplication, which is expected given its allocation-heavy `RealMatrix` design.

## Pitfalls and Migration Traps

**1. Do not mix matrix libraries in one hot path.** Converting between `DMatrixRMaj`, `RealMatrix` and `INDArray` requires copying the entire matrix. A round trip through `double[][]` on a 4,000 × 4,000 matrix is 128 MB of allocation per call.

**2. EJML's sparse types are a different API family.** `DMatrixSparseCSC` and `CommonOps_DSCC` do not accept `DMatrixRMaj` arguments. Sparse solvers (`solveSparse`) also expect specific orderings; feeding a random CSC matrix to a Cholesky solver will throw rather than silently do the slow thing.

**3. Commons Math 4.0 will rename packages.** The beta restructures the tree, so `org.apache.commons.math3.*` imports will not compile unchanged. If you must upgrade, do it behind an interface you own, not by find-and-replace across 200 files.

**4. ND4J's default backend choice is a deployment decision, not an implementation detail.** `nd4j-native-platform` in a Docker image gives you every platform, and the image grows accordingly. It also pulls JavaCPP, which needs a writable temp directory for extracted `.so` files — read-only container filesystems break it unless you mount `/tmp`.

**5. JDK vector API is not a drop-in replacement — yet.** EJML ships optional SIMD paths, and Panama-based vector math is maturing, but do not assume `jdk.incubator.vector` will beat tuned BLAS on a 2,000 × 2,000 multiply. Benchmark, do not assume.

**6. Watch your GC, not just your wall clock.** A "fast" implementation that allocates 4 MB per request shows up as a p99 latency cliff under concurrency. Profile with [async-profiler or JFR](../2026-11-03-jvm-profilers-async-profiler-jfr-visualvm-comparison/) before and after switching libraries.

## Why This Choice Belongs in Your Own Infrastructure

Every one of these libraries is Apache-2.0 and runs entirely inside your own JVM — no license server, no per-core pricing, no data leaving the host. If you are building a pricing engine, a signal-processing service or a scientific batch job, the whole stack fits on a €20/month VPS and your build stays reproducible with [Maven or Gradle pinned in CI](../2026-06-24-jvm-build-tools-gradle-maven-sbt-bazel/).

Operationally, numerical services fail in ways ordinary web services do not: heap exhaustion from matrix allocation, native crashes with no Java stack trace, and latency that degrades linearly with matrix size. That is why [self-hosted JVM monitoring with Scouter, Glowroot or Kamon](../2026-06-04-self-hosted-java-apm-scouter-glowroot-kamon-guide/) is worth wiring up before you ship — you want heap-after-GC and allocation rate on a dashboard, not a support ticket.

## FAQ

**Is EJML faster than Apache Commons Math?**
For dense matrix operations, yes — consistently. EJML generates specialized code over primitive arrays and reuses workspaces, while Commons Math's `RealMatrix` implementations allocate intermediate objects. Commons Math wins only when you need its statistics, distributions or optimizers, not for raw multiplication.

**Does ND4J require a GPU?**
No. The `nd4j-native` backend runs on CPU with OpenBLAS and is fully functional. The CUDA backend is optional and only worth the ~800 MB payload if you actually have a GPU and large tensors.

**Can I use EJML and Commons Math together?**
Yes, and it is a common combination: Commons Math for `DescriptiveStatistics`, distributions and optimizers, EJML for the linear algebra inside the objective function. Just convert matrices once at the boundary instead of back and forth inside a loop.

**Which library should I use for solving sparse systems?**
EJML. It ships sparse LU, Cholesky and QR solvers (`CommonOps_DSCC`, `SolveSparse`) with explicit control over fill-in ordering. Commons Math has essentially no serious sparse support, and ND4J's sparse tensors are aimed at tensor workloads rather than classic sparse linear systems.

**Is Commons Math 4.0 safe to use in production?**
Not yet. 4.0 is at beta (`4.0-beta1` tagged in the repository) and the package layout changes from the 3.x line. Stay on 3.6.1 for production and plan the import migration deliberately.

**How much memory does ND4J need?**
Plan for the natives plus your arrays: ~40 MB of API JARs, several hundred MB of native shared objects, and off-heap memory proportional to your tensor sizes. Cap it explicitly with `-Dorg.bytedeco.javacpp.maxbytes` in containerized deployments.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "EJML vs Apache Commons Math vs ND4J in 2026: Which JVM Math Library Should You Actually Use?",
  "description": "A practical 2026 comparison of EJML 0.46, Apache Commons Math 3.6.1 and ND4J 1.0.0-M2.1 with Maven coordinates, runnable code, a JMH benchmark harness and native-library pitfalls.",
  "datePublished": "2026-11-10",
  "dateModified": "2026-11-10",
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
