---
title: "Kalman Filter Libraries in 2026: filterpy vs pykalman vs TinyEKF vs mherb/kalman"
date: "2026-10-12"
tags: ["scientific-computing", "state-estimation", "python", "cpp", "embedded", "numerical-computing"]
draft: false
cover: "/img/screenshots/tinyekf-altitude-tracking.jpg"
---

Every sensor pipeline starts the same way: you plot the raw readings, see noise, and add a Kalman filter. Then you discover the hard part is not the theory — it is that the four mature open-source implementations make completely different trade-offs, and one of them allocates memory with `malloc` in a control loop while another simply has no floating-point precision option for your microcontroller.

This is a practical comparison of the state-estimation libraries that are actually maintained in 2026, with the API each one really exposes and the situations where each one wins.

![TinyEKF official output: barometer-fused altitude estimate tracking a real trajectory](/img/screenshots/tinyekf-altitude-tracking.jpg "Official TinyEKF output — fused barometric and temperature estimate tracking real altitude data")

## TL;DR — Quick Verdict

**Use filterpy if** you are prototyping in Python and want the widest menu of estimators — linear Kalman, extended, unscented, particle, g-h, least squares, H-infinity and smoothers — in one NumPy library. **Use pykalman if** you need expectation-maximization to *learn* the noise covariances and transition matrices from data instead of guessing them. **Use TinyEKF if** you are deploying to a microcontroller or an embedded target where compile-time memory allocation and a single header are non-negotiable. **Use mherb/kalman if** you are writing modern C++ and want typed, Eigen-based EKF/UKF variants with square-root formulations for numerical stability.

Rule of thumb: **Python work → filterpy or pykalman (learning). Embedded or C++ work → TinyEKF or mherb/kalman.**

## Quick Comparison Table (October 2026)

| Library | Stars | Language | Estimators | Parameter learning | Allocation | License | Last push |
|---|---|---|---|---|---|---|---|
| **filterpy** | 3,882 | Python (NumPy) | KF, EKF, UKF, particle, g-h, least squares, H-infinity, smoothers | Manual tuning | NumPy arrays (heap) | MIT | 2024-02-07 |
| **pykalman** | 1,338 | Python (NumPy) | KF, smoother, EM | Yes — `em()` | NumPy arrays (heap) | New BSD | 2026-04-20 |
| **TinyEKF** | 1,222 | C / C++ header | EKF | Manual tuning | Static (compile-time) | MIT | 2026-04-09 |
| **mherb/kalman** | 1,502 | C++11 header (Eigen) | EKF, SR-EKF, UKF, SR-UKF | Manual tuning | Eigen fixed/dynamic | MIT | 2023-08-24 |

The staleness pattern here is worth noticing: **filterpy has the most stars and the oldest last push**, because it is feature-complete and stable. **mherb/kalman is similarly dormant** (2023) without being abandoned — header-only C++ libraries that work tend not to churn. The two actively developed projects, pykalman and TinyEKF, both had pushes in 2026.

## Decision Matrix: Pick in 10 Seconds

| Your situation | Pick | Why |
|---|---|---|
| Prototyping on a laptop, comparing estimator families | **filterpy** | Widest estimator menu, best-documented examples |
| You don't know Q and R and have offline data | **pykalman** | EM learns noise covariances and matrices |
| Arduino / STM32 / no dynamic allocation allowed | **TinyEKF** | Static arrays, single header, float or double |
| Modern C++ with Eigen, typed state and measurement models | **mherb/kalman** | Compile-time model typing, SR variants |
| Non-linear measurement, need UKF on a PC | **filterpy or mherb/kalman** | Both ship unscented implementations |
| You need a particle filter | **filterpy** | Only one of the four with a particle implementation |
| You need a smoother (offline, whole-trajectory) | **pykalman or filterpy** | RTS smoother available in both |

## filterpy: The Learning and Prototyping Workbench

filterpy (3,882 stars, MIT) is the library behind the widely used *Kalman and Bayesian Filters in Python* course material. If you have read a Kalman filter tutorial with Python code in the last decade, it was probably filterpy.

```bash
pip install filterpy
```

```python
import numpy as np
from filterpy.kalman import KalmanFilter
from filterpy.common import Q_discrete_white_noise

my_filter = KalmanFilter(dim_x=2, dim_z=1)

my_filter.x = np.array([[2.], [0.]])       # initial state: position, velocity
my_filter.F = np.array([[1., 1.],
                        [0., 1.]])          # state transition
my_filter.H = np.array([[1., 0.]])          # measurement function
my_filter.P *= 1000.                        # initial covariance
my_filter.R = 5                             # measurement noise
my_filter.Q = Q_discrete_white_noise(dim=2, dt=0.1, var=0.1)

for z in measurements:
    my_filter.predict()
    my_filter.update(z)
    print(my_filter.x)
```

Two things make filterpy the right default for exploration. First, `Q_discrete_white_noise` builds physically meaningful process noise from a sampling interval and variance, which removes one of the most common sources of badly tuned filters. Second, the uniform `predict()` / `update()` interface means you can swap in `ExtendedKalmanFilter`, `UnscentedKalmanFilter`, `ParticleFilter` or a smoother class without rewriting the surrounding pipeline.

The trade-off is maintenance tempo: the last push predates 2025, so treat it as a stable reference implementation rather than a project expecting new features.

## pykalman: Learn the Noise Model Instead of Guessing It

pykalman (1,338 stars, New BSD, active in 2026) solves the single most annoying practical problem in state estimation: you rarely know `Q` and `R` a priori, and hand-tuning them is a weekend. pykalman exposes `em()` — expectation-maximization — to fit the transition matrices, observation matrices and noise covariances from measurement data.

```bash
pip install pykalman
```

```python
from pykalman import KalmanFilter
import numpy as np

kf = KalmanFilter(
    transition_matrices=[[1, 1], [0, 1]],
    observation_matrices=[[0.1, 0.5], [-0.3, 0.0]],
)

measurements = np.asarray([[1, 0], [0, 0], [0, 1]])   # 3 observations

# Learn parameters, then filter
kf = kf.em(measurements, n_iter=5)
filtered_state_means, filtered_state_covariances = kf.filter(measurements)

# Whole-trajectory estimate (offline smoothing)
smoothed_state_means, smoothed_state_covariances = kf.smooth(measurements)
```

The workflow this enables is genuinely different from filterpy's: **collect data, run `em()` to fit the noise model, inspect the learned covariances, then decide whether they match your physical intuition.** If the learned `Q` says your sensor drifts 10x faster than the datasheet claims, you have found a real bug rather than tuned around it.

Be deliberate about `n_iter`: EM is an iterative optimizer over a non-convex objective, and more iterations is not automatically better. Five to twenty is the usual range before convergence, and you should always confirm with a held-out trajectory rather than the training data.

## TinyEKF: Embedded Deployment Without Surprises

TinyEKF (1,222 stars, MIT, active in 2026) exists because general-purpose matrix libraries are a poor fit for a 32-bit microcontroller. It is a single header using **static, compile-time memory allocation — no `new`, no `malloc`** — and its matrix dimensions are preprocessor macros resolved at compile time.

The trade-off is explicit in the API: you define `EKF_N` (state dimension) and `EKF_M` (measurement dimension) *before* including the header, and the whole library instantiates for exactly those sizes.

```c
#define EKF_N 2          // state: pressure, temperature
#define EKF_M 3          // measurements: baro pressure, baro temp, LM35 temp

#include <tinyekf.h>     // single header, static allocation

static const float EPS = 1e-4;

static const float Q[EKF_N*EKF_N] = { EPS, 0,
                                      0,   EPS };

static const float R[EKF_M*EKF_M] = { EPS, 0,   0,
                                      0,   EPS, 0,
                                      0,   0,   EPS };

static const float F[EKF_N*EKF_N] = { 1, 0,      // process Jacobian (identity here)
                                      0, 1 };

static const float H[EKF_M*EKF_N] = { 1, 0,
                                      0, 1,
                                      0, 1 };

static ekf_t _ekf;

void setup(void) {
    const float pdiag[EKF_N] = { 10.0f, 10.0f };   // initial covariance diagonal
    ekf_initialize(&_ekf, pdiag);
}

void loop(void) {
    float fx[EKF_N], hx[EKF_M], z[EKF_M];

    // ... compute predicted state fx[] and expected measurement hx[] ...

    ekf_predict(&_ekf, fx, F, Q);                   // state + covariance prediction
    if (!ekf_update(&_ekf, z, hx, H, R)) {          // measurement update
        // update failed (singular innovation covariance) — handle explicitly
    }
}
```

That failed-update branch is not decoration. `ekf_update()` returns `false` when the Cholesky factorization of the innovation covariance fails, which happens in the real world when a sensor drops out or reports NaN. Embedded code that ignores the return value will happily propagate garbage.

Two more embedded-specific notes: define `_float_t` to `double` before including the header if single precision is not enough (TinyEKF supports both), and remember that with static allocation you cannot run two differently-sized filters in one translation unit — put each in its own compilation unit.

For the sensing layer that usually feeds a filter like this, our [point cloud processing comparison](../2026-06-08-self-hosted-point-cloud-processing-pcl-open3d-pdal/) covers the heavier 3D side of the same problem.

## mherb/kalman: Typed Models in Modern C++

mherb/kalman (1,502 stars, MIT, header-only C++11) takes the opposite approach to TinyEKF: instead of macro-sized arrays, you define your **state, control and measurement types at compile time as C++ classes**, and the filter is templated on them. It ships four variants — EKF, square-root EKF, UKF, and square-root UKF — built on Eigen.

```cpp
#include <kalman/ExtendedKalmanFilter.hpp>
#include <kalman/UnscentedKalmanFilter.hpp>

typedef float T;

// Types you define once: State<T>, Control<T>,
// PositionMeasurement<T>, OrientationMeasurement<T>, plus
// SystemModel<T>, PositionMeasurementModel<T>, OrientationMeasurementModel<T>

Kalman::ExtendedKalmanFilter<State<T>> ekf;

// Prediction with control input
ekf.predict(sys, u);

// Measurement updates, one per sensor
ekf.update(positionModel, positionMeasurement);
ekf.update(orientationModel, orientationMeasurement);

State<T> estimate = ekf.getState();
```

The reason to prefer this over a hand-rolled filter is the type system doing work for you: a position measurement cannot be accidentally passed to the orientation model, and the Jacobians each model class must provide are checked at compile time. The repository ships a fully commented `examples/Robot1` project that implements a robot localizing against two landmarks — read that file before writing your own models, because it demonstrates the exact set of functions (`f`, `F`, `h`, `H`) each model class has to implement.

If you are building the surrounding stack rather than the filter itself, our roundups of [self-hosted robotics simulation tools](../2026-06-09-self-hosted-robotics-simulation-gazebo-webots-coppeliasim-guide/) and the [open autopilot stack comparison](../2026-10-08-ardupilot-vs-px4-vs-betaflight-open-autopilot-stack-comparison/) show where these estimators sit in a real pipeline.

![mherb/kalman official example output: estimated vs true robot trajectory](/img/screenshots/mherb-kalman-robot-estimate.jpg "Official mherb/kalman Robot1 example — filter estimate against ground truth")

Note the activity date: the last push was 2023. That is normal for a complete header library, but it does mean you should vendor a pinned copy rather than depend on the moving `master` branch in a production build.

## Numerical Pitfalls and Tuning Notes That Save Weekends

**1. Covariance symmetry drift.** Repeated `P = (I − K H) P` updates accumulate asymmetry and can eventually produce negative diagonals. Use the Joseph form (`P = (I−KH)P(I−KH)' + KRK'`) or a square-root variant (mherb's SR-EKF/SR-UKF, or a Cholesky-based implementation) when running millions of updates.

**2. Angle wrap-around.** Any state containing an angle needs normalized innovation: wrap the residual into (−π, π] before the update. Skipping this produces a filter that looks fine for small errors and then jumps violently near the ±π boundary.

**3. `Q` and `R` are not "small is better."** Too-small `R` makes the filter trust a noisy sensor and track noise; too-small `Q` makes it ignore real motion and lag. If you have data, let pykalman's `em()` propose values and validate physically; if you do not, express `Q` in physical units via something like `Q_discrete_white_noise`.

**4. Single precision in embedded targets.** A 32-bit float has about 7 decimal digits. Filters with large covariance magnitudes (1e6) and small measurement noise (1e-4) lose all significance — that is exactly when you set `_float_t` to `double` in TinyEKF, or rescale your units (work in meters rather than millimeters).

**5. Ignoring the update return value.** As noted above, `ekf_update()` returning `false` means the covariance matrix was not factorizable. Handle it: skip the measurement, count the rejections, and raise a diagnostic when rejections cluster.

**6. Divergence detection.** Track the normalized innovation squared (NIS) — the residual normalized by the innovation covariance — and compare its running average against the expected chi-square value for your measurement dimension. A filter that has quietly diverged shows up as NIS growing monotonically long before the estimate looks obviously wrong.

**7. Out-of-sequence measurements.** Multi-sensor systems delivering readings with different latencies cannot just call `update()` in arrival order. Buffer by timestamp and either process in order or implement a retrodiction step; silently reordering measurements is a classic source of position jumps in robotics.

## Which One Should You Actually Use?

Start in **filterpy** to build intuition and compare estimator families on recorded data, because the uniform API and the accompanying course material make iteration cheap. As soon as you have a dataset and no defensible `Q`/`R`, move to **pykalman** and learn them with `em()` — then sanity-check the learned covariances against your sensor datasheets. When the algorithm has to leave the laptop, choose by target: **TinyEKF** for microcontrollers and static-allocation constraints, **mherb/kalman** for C++ projects where Eigen and compile-time model typing are available.

Whatever the deployment target, the test that keeps you honest is the same: replay a recorded trajectory where you know the ground truth, and assert that the filtered estimate beats the raw measurement in RMS error. A filter that loses to its own input is a bug, not a tuning problem.

## FAQ

### Which Kalman filter library is best for Python in 2026?

**filterpy** for breadth — it covers linear, extended, unscented and particle filters plus smoothers in a uniform API. **pykalman** when you need to learn noise covariances and transition matrices from data using expectation-maximization. Many teams use filterpy for prototyping and pykalman to fit the parameters.

### What is the difference between an extended and an unscented Kalman filter?

The extended Kalman filter linearizes a non-linear model around the current estimate using Jacobians — accurate for mild non-linearity, cheap per step. The unscented Kalman filter instead propagates a deterministic set of sigma points through the true non-linear function, which usually gives better accuracy for strongly non-linear measurement models at a higher per-step cost. filterpy and mherb/kalman both provide both.

### Can I run a Kalman filter on a microcontroller?

Yes — that is exactly what TinyEKF is built for. It uses compile-time static allocation (no `malloc`), so memory use is fully predictable, and it runs on Arduino, Teensy and STM32 class hardware. You choose single or double precision by defining `_float_t` before including the header.

### How do I choose the process noise Q and measurement noise R?

If you have recorded data, use pykalman's `em()` to fit them, then check whether the learned values are physically plausible. Without data, derive `Q` from the sampling interval and expected accelerations or drifts — filterpy's `Q_discrete_white_noise(dim, dt, var)` does this for common motion models — and derive `R` from your sensor datasheet variance. Then validate with a NIS consistency check.

### Does pykalman support smoothing, and what is it for?

Yes. `kf.smooth(measurements)` runs an RTS-style smoother that uses the entire trajectory to estimate each state, which is strictly more accurate than filtering for offline analysis — trajectory reconstruction, post-processing logged data, or generating training labels. It cannot be used in real time because it needs future measurements.

### Why does my filter diverge even though the model is correct?

The usual causes, in order of frequency: an unhandled angle wrap-around in the innovation; a covariance matrix that lost symmetry and developed negative diagonal entries from repeated non-Joseph updates; `R` set far too small relative to actual sensor noise; and single-precision arithmetic on a problem whose covariance magnitudes span more orders of magnitude than a 32-bit float can represent. Log NIS and the covariance diagonal to identify which one you have.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Kalman Filter Libraries in 2026: filterpy vs pykalman vs TinyEKF vs mherb/kalman",
  "description": "A practical 2026 comparison of open-source Kalman filter and state estimation libraries — filterpy, pykalman, TinyEKF and mherb/kalman — with install commands, working code, tuning advice and numerical pitfalls.",
  "datePublished": "2026-10-12",
  "dateModified": "2026-10-12",
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
