---
title: "Rust Math Libraries: nalgebra vs ndarray vs cgmath vs glam — Choosing the Right Numeric Crate"
date: "2026-07-23"
tags: ["rust", "math", "linear-algebra", "game-development", "scientific-computing", "rust-crates", "numeric-libraries"]
draft: false
---

## Introduction

Rust has rapidly become a go-to language for performance-critical applications, from game engines to scientific computing and robotics. A key factor in Rust's success is its rich ecosystem of mathematical crates — each optimized for different use cases. But with multiple options for linear algebra, array processing, and computer graphics math, choosing the right crate can be challenging.

This guide compares four leading Rust math libraries: **nalgebra**, **ndarray**, **cgmath**, and **glam**. We'll examine their design philosophies, performance characteristics, API ergonomics, and ideal use cases to help you pick the right tool for your project.

## Comparison Table

| Feature | nalgebra | ndarray | cgmath | glam |
|---------|----------|---------|--------|------|
| **Primary Focus** | Linear algebra & geometry | N-dimensional arrays | Computer graphics math | Game/render math |
| **Stars** | ~3,700 | ~3,500 | ~1,200 | ~1,500 |
| **SIMD Support** | Via simba, nalgebra-sparse | Optional BLAS/LAPACK | No explicit SIMD | Extensive SIMD (SSE2/AVX/NEON/WASM) |
| **Dimensions** | Static & dynamic | Dynamic N-dimensional | Fixed (2D, 3D, 4D) | Fixed (2D, 3D, 4D) |
| **no_std** | Yes (with feature flags) | No | Yes | Yes |
| **GPU Compatible** | Via nalgebra-glm | Limited | Yes (bytemuck support) | Yes |
| **Matrix Decomposition** | SVD, QR, Cholesky, LU, Eigendecomp | Via ndarray-linalg | Basic (inverse, determinant) | Limited |
| **Learning Curve** | Moderate to High | Moderate | Low | Low |
| **Best For** | Robotics, physics sim, scientific | Data science, ML, numerical analysis | Game math, rendering | Real-time graphics, WASM |

## nalgebra: The Linear Algebra Powerhouse

**nalgebra** is the most feature-complete linear algebra library in the Rust ecosystem. It provides a full suite of matrix operations, vector math, transformations (isometries, rotations, similarities), and advanced decompositions (SVD, QR, Cholesky, LU, and eigenvalue computations).

### Installation

```toml
[dependencies]
nalgebra = "0.32"
# Optional: enable nalgebra-glm for GLSL-like API
# nalgebra-glm = "0.18"
```

### Basic Usage

```rust
use nalgebra::{Matrix3, Vector3, DMatrix, SVD};

fn main() {
    // Fixed-size 3x3 matrix
    let a = Matrix3::new(1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0);

    // Vector operations
    let v = Vector3::new(1.0, 2.0, 3.0);
    let result = a * v; // Matrix-vector multiplication

    // Singular Value Decomposition
    let svd = SVD::new(a, true, true);
    println!("Singular values: {:?}", svd.singular_values);

    // Dynamic matrices for runtime-sized data
    let b = DMatrix::from_row_slice(2, 3, &[1.0, 2.0, 3.0, 4.0, 5.0, 6.0]);
    println!("Dynamic matrix:
{}", b);

    // Transformations (3D isometry)
    use nalgebra::{Isometry3, Translation3, UnitQuaternion};
    let iso = Isometry3::from_parts(
        Translation3::new(1.0, 0.0, 0.0),
        UnitQuaternion::from_euler_angles(0.0, std::f32::consts::PI / 2.0, 0.0)
    );
}
```

**Key strengths:** nalgebra shines in robotics, physics simulations, and scientific computing where you need full linear algebra capabilities. The static typing ensures dimension correctness at compile time, and the API is mathematically rigorous.

## ndarray: NumPy for Rust

**ndarray** brings NumPy-style N-dimensional array processing to Rust. Combined with **ndarray-linalg** for LAPACK-backed linear algebra, it's the go-to crate for data science and numerical computing workloads.

### Installation

```toml
[dependencies]
ndarray = "0.15"
ndarray-linalg = { version = "0.16", features = ["openblas"] }
```

### Basic Usage

```rust
use ndarray::{Array2, Array1, arr2, Axis};

fn main() {
    // Create a 3x3 array
    let mut a = Array2::<f64>::zeros((3, 3));
    a[[0, 0]] = 1.0;
    a[[1, 1]] = 2.0;
    a[[2, 2]] = 3.0;

    // Element-wise operations
    let b = &a * 2.0; // Broadcasting
    let c = a.dot(&b); // Matrix multiplication

    // Slicing and views
    let row: Array1<_> = c.row(0).to_owned();
    let sum = c.sum_axis(Axis(0)); // Column-wise sum

    // Create from slice
    let d = arr2(&[[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]);
    println!("Array shape: {:?}, mean: {}", d.shape(), d.mean().unwrap());

    // Statistical operations
    let variance = d.var_axis(Axis(1), 0.0);
    println!("Row variances: {:?}", variance);
}
```

**Key strengths:** ndarray excels at large-scale numerical computation, data manipulation, and machine learning preprocessing. The broadcasting semantics are familiar to NumPy users, making it easy to port Python numerical code to Rust. For serious linear algebra, pair it with **ndarray-linalg** which provides BLAS/LAPACK bindings.

## cgmath: Graphics-First Math

**cgmath** is designed specifically for computer graphics applications. It provides the essential vector, matrix, and quaternion types needed for rendering, camera math, and shader computations.

### Installation

```toml
[dependencies]
cgmath = "0.18"
```

### Basic Usage

```rust
use cgmath::{Matrix4, Vector3, Vector4, Point3, Quaternion, Rad, Deg, perspective, InnerSpace};

fn main() {
    // Vector operations
    let v1 = Vector3::new(1.0, 0.0, 0.0);
    let v2 = Vector3::new(0.0, 1.0, 0.0);
    let cross = v1.cross(v2);
    let dot = v1.dot(v2);

    // Matrix transformations
    let translation = Matrix4::from_translation(Vector3::new(2.0, 0.0, 0.0));
    let rotation = Matrix4::from_angle_z(Deg(90.0));
    let transform = translation * rotation;

    // Homogeneous coordinates
    let point = Point3::new(1.0, 2.0, 3.0);
    let transformed = transform * point;

    // Quaternion rotation
    let quat = Quaternion::from_axis_angle(
        Vector3::unit_z(),
        Rad(std::f32::consts::PI / 4.0)
    );

    // Projection matrix
    let projection: Matrix4<f32> = perspective(Deg(60.0), 16.0 / 9.0, 0.1, 100.0);
    println!("Projection matrix created");
}
```

**Key strengths:** cgmath is intentionally focused and lightweight. It doesn't try to be everything — just the math structures you need for OpenGL/Vulkan/WGPU rendering, camera systems, and basic physics. Its `swizzle!` macro makes shader-style vector swizzling ergonomic.

## glam: The Performance Champion

**glam** is a relatively newer entrant that has quickly gained popularity, especially in the Rust gamedev community. It's built from the ground up for maximum performance with extensive SIMD optimization.

### Installation

```toml
[dependencies]
glam = "0.25"
```

### Basic Usage

```rust
use glam::{Vec3, Vec4, Mat4, Quat, Affine3A, Vec3A};

fn main() {
    // SIMD-accelerated vectors (Vec3A uses 16-byte alignment)
    let v1 = Vec3A::new(1.0, 0.0, 0.0);
    let v2 = Vec3A::new(0.0, 1.0, 0.0);
    let cross = v1.cross(v2);

    // Affine transform (faster than Mat4 for common cases)
    let transform = Affine3A::from_rotation_translation(
        Quat::from_rotation_z(1.57),
        Vec3::new(5.0, 0.0, 0.0)
    );

    // Matrix operations
    let view = Mat4::look_at_rh(
        Vec3::new(0.0, 5.0, 10.0),
        Vec3::ZERO,
        Vec3::Y
    );
    let proj = Mat4::perspective_rh(1.2, 16.0 / 9.0, 0.1, 100.0);
    let vp = proj * view;

    // Convert to byte array for GPU upload
    let bytes: &[u8] = vp.as_ref().as_ref();
    println!("MVP matrix bytes: {} bytes", bytes.len());

    // 4D vector with swizzling
    let v4 = Vec4::new(1.0, 2.0, 3.0, 4.0);
    let v3_from_swizzle: Vec3 = v4.xyz();
    println!("Swizzled: {:?}", v3_from_swizzle);
}
```

**Key strengths:** glam is the go-to choice for game engines, real-time rendering, and WASM targets. Its `Vec3A` type (16-byte aligned) leverages SSE2/AVX/NEON for significant speedups. The `Affine3A` type is particularly efficient for common transform operations, avoiding the overhead of full 4x4 matrix multiplication.

## Performance Considerations

For throughput-critical code paths, library choice matters significantly:

- **glam** leads in pure vector/matrix throughput due to aggressive SIMD optimization. Benchmarks show 2-4x speedups over nalgebra for simple transform chains.
- **nalgebra** with **simba** provides SIMD-accelerated linear algebra, but its generality incurs some overhead on simple operations.
- **ndarray** with optimized BLAS (OpenBLAS/MKL) is fastest for large matrix operations (1000x1000+) but slower for small fixed-size math.
- **cgmath** occupies the middle ground — faster than nalgebra for graphics math but without glam's SIMD specialization.

For WASM targets, glam's WASM SIMD support makes it the clear winner for browser-based graphics applications.

## Choosing the Right Library

**Use nalgebra if:** You need comprehensive linear algebra (SVD, eigenvalue decomposition, Cholesky), you're building a robotics/control system, or you need dimension-generic code with strong compile-time guarantees.

**Use ndarray if:** You're doing data science, numerical analysis, or working with large multi-dimensional datasets. It's the closest Rust equivalent to NumPy and pairs well with data processing pipelines.

**Use cgmath if:** You have an existing codebase using cgmath, need a mature and stable API, or want a simpler learning curve for graphics-focused math.

**Use glam if:** Performance is your top priority, you're targeting WASM, or you're building a game engine / real-time application. Its SIMD-first architecture delivers the best throughput for common graphics math operations.

## FAQ

### Can I use multiple math libraries in the same project?

Yes, and this is common in larger Rust projects. For example, you might use ndarray for data preprocessing, nalgebra for optimization/estimation (Kalman filters), and glam for rendering. Just be aware of data conversion overhead between libraries — types like `nalgebra::Vector3` and `glam::Vec3` require explicit conversion functions.

### Does nalgebra replace ndarray for data science?

Not exactly. nalgebra focuses on mathematical rigor and linear algebra, while ndarray focuses on general N-dimensional array operations and NumPy-like ergonomics. For a data science pipeline involving CSV parsing, data cleaning, and statistical analysis, ndarray is more appropriate. For optimization, control theory, and rigorous geometry, nalgebra is superior.

### How does glam achieve such high performance?

glam uses explicit SIMD intrinsics (SSE2, SSE4.1, AVX2, NEON) via the `std::arch` module. Its `Vec3A` type uses 16-byte alignment to enable efficient SIMD loads/stores, while `Mat4` is stored column-major for efficient matrix-vector multiplication. The library is also designed to compile well on WASM with SIMD128 support, making it the best choice for browser graphics applications.

### Is there a Rust equivalent to MATLAB?

While no single crate fully replicates MATLAB, a combination of nalgebra (linear algebra), ndarray (arrays), plotters (visualization), and the `rust-numpy` crate (Python interop) comes close. For interactive exploration, the `evcxr` REPL provides a Jupyter-like experience with Rust kernels. See our guide on [open-source mathematical computing tools](../2026-05-11-open-source-mathematical-computing-sagemath-octave-maxima-guide/) for more alternatives.

### Are these libraries safe for production use?

All four libraries are widely used in production. nalgebra powers robotics frameworks and physics engines (Rapier uses it). ndarray is used in ML pipelines and scientific computing infrastructure. glam is used by Bevy Engine, one of Rust's most popular game engines. cgmath has been stable for years and is used in many rendering engines. All four have active maintenance and thorough test suites.

### How do these libraries handle arbitrary-precision arithmetic?

None of these libraries natively support arbitrary precision — they all operate on native f32/f64 types. For arbitrary precision, use the `rug` or `num-bigint` crates separately. For rational arithmetic, `num-rational` is available. These can interoperate with the math libraries through conversion at computation boundaries.

## Why Self-Host Your Numeric Computing Stack?

Self-hosting scientific computing infrastructure gives you full control over your data, algorithms, and computational resources. Unlike cloud-based numerical platforms that charge per compute-hour and require uploading sensitive data, a self-hosted setup lets you run Rust-based numerical pipelines on your own hardware with zero recurring costs. The combination of Rust's performance and these math libraries means you can process terabyte-scale datasets on modest hardware that would require expensive cloud instances in Python.

For scientific data management, see our guide on [self-hosted scientific data management with iRODS and Rucio](../2026-06-09-self-hosted-scientific-data-management-irods-rucio-datalad-guide/). For team-based numerical computing platforms, check out our [open-source mathematical computing comparison](../2026-05-11-open-source-mathematical-computing-sagemath-octave-maxima-guide/). If you're interested in the Rust ecosystem more broadly, our [Rust error handling guide](../2026-06-22-rust-error-handling-anyhow-thiserror-eyre-guide/) covers another essential part of building reliable Rust applications.

---

**💡 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rust Math Libraries: nalgebra vs ndarray vs cgmath vs glam — Choosing the Right Numeric Crate",
  "description": "Comprehensive comparison of Rust math libraries nalgebra, ndarray, cgmath, and glam. Includes code examples, performance analysis, and guidance for choosing the right numeric crate for game development, scientific computing, and data science.",
  "datePublished": "2026-07-23",
  "dateModified": "2026-07-23",
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
