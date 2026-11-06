---
title: "Geant4 vs GATE vs TOPAS in 2026: Monte Carlo Simulation for Medical Physics"
date: "2026-11-07"
tags: ["geant4", "gate", "topas", "monte-carlo", "medical-physics", "scientific-computing", "simulation", "radiotherapy"]
draft: false
cover: "/img/screenshots/geant4-event-display.jpg"
description: "Geant4 vs GATE vs TOPAS compared for 2026: real build steps, macro examples, licensing, physics-list traps, and DICOM commissioning workflows for radiotherapy and imaging."
---

A proton therapy plan is only as good as the dose engine behind it. You need roughly 10⁸ particle histories to get 1% statistical uncertainty in a small field, and every one of those histories has to traverse the same geometry, the same material composition, and the same physics processes your treatment planning system assumes. Get the physics list wrong and your Bragg peak shifts by two millimetres — which, at the distal edge of a target volume, is the difference between tumour control and a complication.

Monte Carlo transport is the ground truth that everything else is validated against. Three codebases dominate the field, and choosing between them in 2026 is a decision about **who writes your geometry**: you, in C++; a physicist, in macro files; or a clinical team, in parameter lists.

## TL;DR — Quick Verdict

**Use Geant4 when you need control.** It's the engine — 872 stars, actively released (v11.4.3, October 2026), C++17, and the substrate the other two are built on. You write the detector, you pick the physics, you own the validation.

**Use GATE when you're doing imaging or need reproducible clinical geometry.** 285 stars, v9.4.2, LGPL-3.0, macro-driven through a Python layer on top of Geant4. It ships the scanner geometries (PET, SPECT, CT) already built, which saves months.

**Use TOPAS when you're in a clinical proton or photon therapy group** and want validated beam models without maintaining C++. It has no public repository and is licensed free of charge for academic use.

**Do not pick Geant4 to "save time."** You will not. Pick it to avoid a ceiling you'd otherwise hit in year two.

## Head-to-Head Comparison

| Dimension | Geant4 | GATE | TOPAS |
|---|---|---|---|
| Repository | `Geant4/geant4` | `OpenGATE/Gate` | No public repo |
| Stars | **872 ⭐** | **285 ⭐** | n/a |
| Latest release | **v11.4.3** (2026-10-01) | **v9.4.2** (2026-03-23) | Versioned binaries |
| Last commit | **2026-10-01** | **2026-10-15** | Closed development |
| License | Geant4 Software License | **LGPL-3.0** | Free for academic / non-commercial |
| Language | C++17 | C++ core, Python/macro interface | Parameter files |
| Input style | Compiled C++ | Macro commands | Text parameter file |
| Learning curve | Months | Weeks | Days |
| Imaging geometries included | No | **Yes** (PET, SPECT, CT) | Some |
| Therapy beam models included | No | Partial | **Yes** |
| Multithreaded | Yes | Yes (via Geant4) | Yes |
| Best fit | Custom physics, detector R&D | Preclinical imaging, dosimetry | Clinical radiotherapy |

Star counts and release dates are live as of this writing. TOPAS has no GitHub presence at all — if you search for it and find nothing, that is expected, not a sign the project is dead.

## Decision Matrix — Pick in 10 Seconds

| Your situation | Pick | Why |
|---|---|---|
| Designing a novel detector or calorimeter | **Geant4** | Full control over geometry and sensitive volumes |
| PET/SPECT scanner simulation | **GATE** | Scanner geometries and digitizer chains ship built-in |
| Clinical proton beam commissioning | **TOPAS** | Validated beam models, parameter files, no compiling |
| Microdosimetry at cellular scale | **Geant4** | Custom scoring and very fine geometry required |
| Teaching a medical physics course | **GATE** | Macros are readable and run without a compiler |
| Production code that must be audited line by line | **Geant4** | The licences of both wrappers add a layer you can't edit |
| Vendor-supplied linac model | **TOPAS** | Usually the only option the vendor supports |
| You need it running this week | **GATE via conda** | Single command install, no CMake |

## Geant4 — The Engine

Geant4 is a toolkit, not an application. There is no `geant4 input.mac` binary. You write a program that builds a geometry, registers physics, and runs a run manager. Everything else — scoring, visualization, output format — is your responsibility.

Build from source with CMake. This is the only supported route; distro packages lag badly.

```bash
git clone https://github.com/Geant4/geant4.git
cmake -S geant4 -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DGEANT4_INSTALL_DATA=ON \
  -DGEANT4_USE_OPENGL_X11=ON \
  -DGEANT4_USE_QT=ON
cmake --build build -j"$(nproc)"
cmake --install build --prefix /opt/geant4
source /opt/geant4/bin/geant4.sh
```

`GEANT4_INSTALL_DATA=ON` is not optional in practice. Without the cross-section datasets, runs either fail or — worse — fall back to physics you didn't ask for.

A minimal detector construction looks like this:

```cpp
#include "G4VUserDetectorConstruction.hh"
#include "G4NistManager.hh"
#include "G4Box.hh"
#include "G4LogicalVolume.hh"
#include "G4PVPlacement.hh"
#include "G4SystemOfUnits.hh"

class Detector : public G4VUserDetectorConstruction {
public:
  G4VPhysicalVolume* Construct() override {
    auto* nist = G4NistManager::Instance();
    auto* water = nist->FindOrBuildMaterial("G4_WATER");
    auto* lead  = nist->FindOrBuildMaterial("G4_Pb");

    auto* worldSolid = new G4Box("world", 50.*cm, 50.*cm, 50.*cm);
    auto* worldLV = new G4LogicalVolume(worldSolid, water, "world");
    auto* worldPV = new G4PVPlacement(nullptr, {}, worldLV, "world", nullptr, false, 0);

    auto* shieldSolid = new G4Box("shield", 10.*cm, 10.*cm, 2.*cm);
    auto* shieldLV = new G4LogicalVolume(shieldSolid, lead, "shield");
    new G4PVPlacement(nullptr, G4ThreeVector(0, 0, 20.*cm),
                      shieldLV, "shield", worldLV, false, 0);

    return worldPV;
  }
};
```

The physics list is where most commissioning errors originate. For radiotherapy and dosimetry, `G4EmStandardPhysics_option4` gives the most accurate electromagnetic transport, and hadronic interactions for proton therapy need a high-precision model:

```cpp
#include "G4PhysListFactory.hh"

auto* factory = new G4PhysListFactory();
G4VModularPhysicsList* physics = factory->GetPhysListFromName("QGSP_BIC_HP");
```

![Geant4 visualisation of a particle shower through detector geometry](/img/screenshots/geant4-event-display.jpg "Event display from the CaTS example shipped in the official Geant4 repository, showing tracks through a calorimeter")

The tradeoff is honest and brutal: you get exactly the physics and geometry you specify, and you get to debug exactly the physics and geometry you specify. Detector R&D groups live in this mode for years and consider it a feature. Clinical groups tend to consider it a staffing problem.

## GATE — The Imaging Workbench

GATE wraps Geant4 in a macro interpreter with a Python layer on top. The pitch is that a physicist can describe a PET scanner in a text file without touching a compiler, and for once the pitch is accurate — the scanner geometries, dead-time models, and digitizer chains are already written.

Installation is genuinely one command, which is not something you can say about Geant4:

```bash
conda create -n gate -c conda-forge python=3.11
conda activate gate
conda install -c conda-forge gate
```

A working simulation is a macro file. This is a complete, runnable cylinder-and-source setup:

```text
/gate/geometry/setMaterialDatabase GateMaterials.db

/gate/world/geometry/setXLength 1. m
/gate/world/geometry/setYLength 1. m
/gate/world/geometry/setZLength 1. m
/gate/world/setMaterial Air

/gate/world/daughters/name phantom
/gate/world/daughters/insert cylinder
/gate/phantom/geometry/setRmax 50. mm
/gate/phantom/geometry/setHeight 200. mm
/gate/phantom/setMaterial Water
/gate/phantom/vis/forceSolid
/gate/phantom/placement/setTranslation 0. 0. 0. mm

/gate/phantom/daughters/name crystal
/gate/phantom/daughters/insert box
/gate/crystal/geometry/setXLength 4. mm
/gate/crystal/geometry/setYLength 4. mm
/gate/crystal/geometry/setZLength 20. mm
/gate/crystal/setMaterial BGO

/gate/source/addSource mysource gps
/gate/source/mysource/gps/particle gamma
/gate/source/mysource/gps/energytype Mono
/gate/source/mysource/gps/monoenergy 511. keV
/gate/source/mysource/gps/type Volume
/gate/source/mysource/gps/shape Cylinder
/gate/source/mysource/gps/radius 5. mm
/gate/source/mysource/gps/halfz 10. mm

/gate/application/setNumberOfPrimariesPerRun 100000
/gate/application/startDAQ
```

That is the entire learning curve in one file — readable by someone who has never compiled C++.

Its limit is the same as its strength: when you need a geometry GATE doesn't model, or a scoring quantity its actors don't expose, you drop into C++ anyway, and now you're maintaining C++ *inside* a wrapper whose internals you also have to understand.

## TOPAS — The Clinical Route

TOPAS is Geant4 with the detector geometry decisions already made for you, exposed as a plain-text parameter file. There is no GitHub repository and no open source licence: development is by a collaboration, binaries are distributed free of charge for academic and non-commercial use, and commercial use requires a separate arrangement.

For a clinical proton or photon therapy group this is usually the right trade. Dose engines used for patient treatment must be validated end-to-end, and "someone in the group forked the geometry code last year" is a hard position to defend in an audit. TOPAS parameter files are reviewable by a medical physicist who does not program, which matters more than elegance.

The cost is real: you cannot fix a bug yourself, you cannot inspect the transport code, and you are tied to whatever components the collaboration has chosen to model. If your accelerator or nozzle isn't supported, you are waiting on someone else's release schedule.

## Where All Three Bite You

**Physics list drift is the silent killer.** Switching from `G4EmStandardPhysics` to `option4` shifts dose deposition by a few percent in heterogeneous media — enough to fail commissioning. Pin the physics list in your repository and treat any change as a re-commissioning event, not a code review.

**Production cuts are not "just a performance knob."** The default range cut is 0.7 mm. In a 2 mm air cavity or a thin skin layer, that cut can suppress secondary electron transport entirely. For microdosimetry you need cuts at the micron scale, and the runtime cost is severe.

**DICOM Hounsfield units to material conversion** is the single largest error source in CT-based simulations. Density calibration curves are scanner-specific. If you reuse a curve from another institution's CT, your dose differences will look like physics bugs when they are actually material-assignment bugs.

**Missing cross-section data fails quietly.** If `G4LEDATA` or `G4ENSDFSTATEDATA` isn't set, Geant4 may still run. It just won't be running the physics you validated. Check the environment variables in every container image.

**Multithreaded runs do not reproduce by default.** Seed handling differs between single- and multi-threaded modes. If you validate in single-threaded and deploy multi-threaded, you are validating a different program.

**Variance reduction changes your answer.** Importance sampling and cross-section biasing reduce runtime by orders of magnitude and also modify the estimator. Any variance reduction scheme must be validated against an analogue run, not assumed correct.

## Why Self-Host These Workloads?

All three are embarrassingly parallel and none of them need a cloud vendor. A single 64-core node runs a few million histories per hour, and your DICOM data never leaves the building — which, for patient images, is usually the deciding argument. Batch systems (Slurm, HTCondor) integrate trivially because each run is an independent process reading a text input.

For the analysis side, our [particle physics data analysis guide](../2026-06-10-self-hosted-particle-physics-root-uproot-awkward-guide/) covers ROOT, Uproot, and Awkward Array — the toolchain you'll use to read the ntuples these simulations produce. If your interest is electromagnetic field solving rather than particle transport, the [electromagnetic simulation comparison](../2026-06-10-self-hosted-electromagnetic-simulation-meep-openems-gprmax/) covers a different family of solvers, and the [scientific simulation overview](../2026-06-08-self-hosted-scientific-simulation-openfoam-elmer-calculix/) covers continuum codes.

## FAQ

### Is Geant4 free for commercial use?

Yes, under the Geant4 Software License, which is BSD-like and permits commercial use and redistribution with attribution. This is a genuine advantage over TOPAS, whose free licence is limited to academic and non-commercial work.

### Can GATE replace Geant4 entirely?

Only if your problem fits GATE's abstractions. GATE inherits all of Geant4's physics, so accuracy is equivalent for the same physics list. The limitation is geometric and scoring flexibility: novel detector concepts usually require dropping to C++, at which point you are using Geant4 with extra steps.

### How long does a typical simulation take?

A clinical proton beam model with 10⁸ primaries and a full nozzle geometry takes hours on 32 cores. A preclinical PET scanner simulation at 10⁷ primaries runs in tens of minutes. Runtime scales linearly with primaries and inversely with production cut size — the cut matters more than the core count.

### Do I need a GPU?

No. None of these three have production GPU transport. They are CPU-bound and multi-threaded. Effort spent on variance reduction returns far more than effort spent on hardware.

### What is the minimum hardware to get started?

Any x86-64 Linux machine with 8 GB of RAM will compile and run all three for teaching-scale problems. For real commissioning work, budget 32 or more cores and 64 GB of RAM, plus a few hundred gigabytes for the Geant4 datasets and output ntuples.

### Which one should a medical physics department standardise on?

TOPAS for clinical treatment planning support, GATE for imaging research, Geant4 for anything where you need to modify the transport or geometry at a level the wrappers don't expose. Many departments run two of the three, and the duplication is justified — validation cost is lower than the cost of forcing one tool into the wrong role.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Geant4 vs GATE vs TOPAS in 2026: Monte Carlo Simulation for Medical Physics",
  "description": "Geant4 vs GATE vs TOPAS compared for 2026: build steps, macro examples, licensing, physics-list traps, and DICOM commissioning workflows.",
  "datePublished": "2026-11-07",
  "dateModified": "2026-11-07",
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
