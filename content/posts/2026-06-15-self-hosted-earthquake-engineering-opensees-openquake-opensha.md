---
title: "Self-Hosted Earthquake Engineering & Seismic Hazard Analysis: OpenSees vs OpenQuake vs OpenSHA"
date: "2026-06-15"
tags: ["earthquake-engineering", "seismic-hazard", "structural-analysis", "scientific-computing", "simulation", "opensource"]
draft: false
---

## Introduction

Earthquake engineering relies on sophisticated computational tools to predict structural responses, assess seismic hazards, and inform building codes. Whether you are a structural engineer designing a high-rise, a researcher modeling fault rupture scenarios, or a government agency conducting regional risk assessments, open-source seismic analysis platforms provide professional-grade capabilities without the six-figure licensing costs of commercial alternatives.

This guide compares three leading open-source earthquake engineering platforms: **OpenSees** (Open System for Earthquake Engineering Simulation), **OpenQuake Engine** (Global Earthquake Model's hazard and risk calculator), and **OpenSHA** (Open Seismic Hazard Analysis). Each serves a distinct role in the seismic analysis workflow — from structural response simulation to probabilistic hazard assessment.

## Comparison Table

| Feature | OpenSees | OpenQuake Engine | OpenSHA |
|---------|----------|------------------|---------|
| **Primary Focus** | Structural & geotechnical response simulation | Probabilistic seismic hazard & risk analysis | Seismic hazard curve calculation |
| **Language** | C++ with Tcl/Python bindings | Python | Java |
| **License** | Custom open-source | AGPL v3.0 | BSD 3-Clause |
| **GitHub Stars** | 773 | 439 | 29 |
| **Last Updated** | June 2026 | June 2026 | June 2026 |
| **Developer** | UC Berkeley / PEER | GEM Foundation | USGS / SCEC |
| **Container Support** | Community Docker images | Official Docker image | JAR-based, Docker-configurable |
| **Best For** | Nonlinear time-history analysis, soil-structure interaction | Large-scale hazard mapping, portfolio risk | Site-specific hazard curves, attenuation relationships |
| **Parallel Computing** | OpenSeesMP/SP for distributed | Built-in Celery task queue | Single-machine |
| **GUI Available** | OpenSeesPy + external tools | Web UI (IPT) | Java GUI + command line |

## OpenSees: The Structural Simulation Workhorse

OpenSees (Open System for Earthquake Engineering Simulation), developed at UC Berkeley's Pacific Earthquake Engineering Research (PEER) Center, is the dominant open-source platform for nonlinear structural and geotechnical analysis. With over 770 stars on GitHub and continuous development since 1999, it powers research at hundreds of universities worldwide.

OpenSees excels at:
- **Nonlinear time-history analysis** of frames, bridges, and foundations
- **Soil-structure interaction** with advanced constitutive models
- **Performance-based earthquake engineering** with incremental dynamic analysis
- **Distributed computing** via OpenSeesMP (multi-process) and OpenSeesSP (single-program parallel)

### Installing OpenSees with Docker

OpenSees can run in a containerized environment for reproducible simulations:

```bash
# Pull the community-maintained OpenSees Docker image
docker pull silviamazzoni/opensees:latest

# Run an interactive OpenSees session
docker run -it --rm \
  -v $(pwd)/models:/home/opensees/models \
  silviamazzoni/opensees:latest \
  OpenSees /home/opensees/models/my_analysis.tcl
```

For Python users, OpenSeesPy provides native Python bindings:

```bash
# Install OpenSeesPy via pip
pip install openseespy

# Verify installation
python3 -c "import openseespy.opensees as ops; ops.wipe(); print('OpenSeesPy ready')"
```

A basic nonlinear frame analysis in OpenSeesPy:

```python
import openseespy.opensees as ops

# Create model
ops.wipe()
ops.model('basic', '-ndm', 2, '-ndf', 3)

# Define nodes (bottom to top of a column)
ops.node(1, 0.0, 0.0)
ops.node(2, 0.0, 3.0)

# Fix base
ops.fix(1, 1, 1, 1)

# Define material (steel)
ops.uniaxialMaterial('Steel01', 1, 345.0, 200000.0, 0.01)

# Define section and element
ops.section('Elastic', 1, 200000.0, 1.0e-4, 1.0)
ops.geomTransf('Linear', 1)
ops.element('elasticBeamColumn', 1, 1, 2, 1.0e-2, 200000.0, 1.0, 1)

# Apply load and analyze
ops.timeSeries('Linear', 1)
ops.pattern('Plain', 1, 1)
ops.load(2, 10.0, 0.0, 0.0)
ops.system('BandGeneral')
ops.analysis('Static')
ops.analyze(1)

print(f"Top displacement: {ops.nodeDisp(2,1):.4f} m")
ops.wipe()
```

## OpenQuake Engine: Hazard and Risk at Scale

The OpenQuake Engine, maintained by the Global Earthquake Model (GEM) Foundation in Pavia, Italy, is a Python-based platform for probabilistic seismic hazard analysis (PSHA) and earthquake risk assessment. With 439 stars on GitHub and active development, it is the standard tool for national hazard mapping and catastrophe modeling.

OpenQuake's strengths:
- **Classical PSHA** computes hazard curves and uniform hazard spectra
- **Event-based PSHA** generates stochastic earthquake catalogs and ground-motion fields
- **Scenario risk** calculates damage and loss for specific earthquake events
- **Distributed computing** via Celery workers for large-scale calculations
- **Web-based tools** including the Integrated Platform Toolkit (IPT) for input preparation

### Installing OpenQuake Engine with Docker

GEM provides an official Docker image for the engine:

```bash
# Pull the official OpenQuake Engine Docker image
docker pull openquake/engine:latest

# Run the engine in a container
docker run -d --name oq-engine \
  -p 8800:8800 \
  -v $(pwd)/oqdata:/home/openquake/oqdata \
  openquake/engine:latest

# Run a hazard calculation
docker exec oq-engine oq engine --run \
  /home/openquake/oqdata/demos/hazard/AreaSourceClassicalPSHA/job.ini

# View results
docker exec oq-engine oq engine --list-outputs
```

For a production deployment, you can leverage Docker Compose with Celery workers:

```yaml
version: '3.8'
services:
  oq-engine:
    image: openquake/engine:latest
    ports:
      - "8800:8800"
    volumes:
      - ./oqdata:/home/openquake/oqdata
    environment:
      - OQ_DISTRIBUTE=celery
    command: oq dbserver start && oq webui start 0.0.0.0:8800

  celery-worker:
    image: openquake/engine:latest
    volumes:
      - ./oqdata:/home/openquake/oqdata
    depends_on:
      - oq-engine
      - redis
    command: celery -A openquake.engine.worker worker --loglevel=info

  redis:
    image: redis:7-alpine
```

## OpenSHA: Site-Specific Hazard Analysis

OpenSHA (Open Seismic Hazard Analysis), developed by the USGS and SCEC (Southern California Earthquake Center), is a Java-based platform for computing site-specific seismic hazard curves and spectra. While smaller in scope than OpenQuake (29 stars), it offers deep integration with USGS hazard models and attenuation relationships.

OpenSHA is particularly valuable for:
- **Site-specific PSHA** using the latest NGA-West2 ground motion models
- **Disaggregation analysis** identifying controlling earthquake scenarios
- **Hazard curve computation** with multiple ground-motion prediction equations
- **Integration with USGS earthquake catalogs** and fault databases
- **Educational use** with the built-in graphical interface

### Running OpenSHA

```bash
# Download the latest release
wget https://github.com/opensha/opensha/releases/latest/download/OpenSHA.jar

# Run the GUI
java -Xmx4g -jar OpenSHA.jar

# Or use the command-line interface for batch processing
java -cp OpenSHA.jar org.opensha.apps.SiteHazardCurve \
  --site 34.05,-118.25 \
  --output hazard_results.csv
```

## Choosing the Right Platform

The choice between OpenSees, OpenQuake, and OpenSHA depends on your workflow:

- **Structural engineers** performing detailed building analysis should start with OpenSees for its unmatched nonlinear modeling capabilities and distributed computing support.
- **Seismologists and hazard modelers** conducting regional or national PSHA should use OpenQuake Engine for its scalability, reproducibility, and comprehensive GMPE library.
- **Geotechnical engineers** needing site-specific hazard curves should consider OpenSHA for its seamless USGS data integration and modern NGA-West2 ground motion models.

These tools are complementary rather than competitive. In a typical large-scale project, you might use OpenQuake to generate hazard curves for a region, OpenSHA to refine site-specific estimates, and OpenSees to simulate the structural response under the resulting ground motions.

## Deployment Considerations

All three platforms benefit from containerization for reproducibility. OpenQuake and OpenSees have active Docker communities. For large simulations, consider deploying on Kubernetes with persistent volumes for model storage and result archiving. Scientific computing workloads often require significant RAM (16-64 GB) and CPU cores — cloud instances or on-premises HPC clusters are recommended for regional-scale PSHA or detailed nonlinear analyses.

Tools like Kubernetes and Docker Compose simplify deploying these simulation environments. Check our [Docker Compose vs Podman Compose comparison](../docker-compose-vs-podman-compose-vs-nerdctl-container-compose-tools-2026/) for container orchestration options.

For managing complex engineering infrastructure, see our [infrastructure drift detection guide](../self-hosted-infrastructure-drift-detection-driftctl-cloud-custodian-opentofu-guide-2026/).


## Deployment Architecture for Seismic Computing

Running OpenSees, OpenQuake, and OpenSHA in production requires thoughtful infrastructure planning. Seismic hazard computations are CPU-bound and embarrassingly parallel — a 200,000-year PSHA catalog splits naturally across worker nodes. Here is how to architect your deployment:

**Compute Layer**: For regional PSHA with OpenQuake, provision 16-32 vCPUs with 32-64 GB RAM on cloud instances (AWS c5/m5 or equivalent). OpenSees nonlinear time-history analyses are typically single-node but benefit from high clock speeds. Use spot/preemptible instances for batch simulation campaigns to reduce costs by 60-80%.

**Storage Architecture**: Seismic simulation generates substantial output: a regional OpenQuake PSHA can produce 50-200 GB of ground-motion fields, hazard curves, and disaggregation matrices. Use network-attached storage (NFS) or object storage (MinIO, S3) with a lifecycle policy to archive raw results after post-processing. OpenSees binary output files should be converted to HDF5 for long-term archival and cross-tool compatibility.

**Containerization with Docker**: All three tools benefit from containerization for reproducible research. Build Docker images with pinned dependency versions and include your organization's ground motion prediction equations and site-specific velocity models. Use Docker Compose for multi-service deployments (engine + workers + database) and Kubernetes for production-scale simulation farms. See our [container orchestration guide](../docker-compose-vs-podman-compose-vs-nerdctl-container-compose-tools-2026/) for deployment patterns.

**Orchestration and Job Scheduling**: For large-scale simulation campaigns, integrate with Slurm (HPC) or Kubernetes Job objects. OpenQuake's Celery workers scale horizontally — add workers as needed for peak campaigns. Set resource limits and use priority queues to ensure time-sensitive regulatory analyses complete before research simulations.

**Data Management and Collaboration**: Store simulation inputs (source models, fragility curves, exposure data) in version-controlled repositories. Use Git LFS for large binary files. Tag input datasets with SHA hashes to ensure reproducibility. For collaborative engineering workflows, deploy a shared simulation server with JupyterHub for browser-based analysis access across your team, similar to the patterns covered in our [infrastructure drift detection guide](../self-hosted-infrastructure-drift-detection-driftctl-cloud-custodian-opentofu-guide-2026/).

For managing engineering simulation infrastructure at scale, consistent configuration management is essential. Our [chaos engineering guide](../self-hosted-chaos-engineering-litmus-chaos-mesh-chaos-toolkit-guide-2026/) covers testing system resilience under failure conditions — critical for ensuring simulation jobs recover gracefully from node failures during multi-day computation campaigns.

## FAQ

### Do I need a PhD to use these tools?

Not necessarily. OpenSHA and OpenQuake's IPT provide graphical interfaces that are accessible to practicing engineers. OpenSees requires more expertise — expect a learning curve for nonlinear modeling. All three have extensive documentation, tutorials, and active community forums.

### Can I use these for commercial projects?

Yes. OpenSHA (BSD license) is the most permissive. OpenQuake (AGPL v3) requires careful consideration for integrated services — consult your legal team. OpenSees uses a custom open-source license that permits commercial use with attribution.

### How accurate are open-source seismic tools compared to commercial software?

Research consistently shows that open-source platforms produce results comparable to commercial codes like SAP2000, ETABS, and LS-DYNA when properly configured. The 2015 PEER blind prediction contest demonstrated that OpenSees models matched or exceeded commercial code accuracy. The key variable is user expertise, not the software.

### What hardware do I need for regional-scale PSHA?

For OpenQuake, a typical national hazard map computation requires 16-32 CPU cores and 32-64 GB RAM. The Celery-based architecture allows distributing work across multiple machines. Cloud providers like AWS (c5/m5 instances) or on-premises HPC clusters work well. A single-site PSHA calculation completes in seconds on a laptop.

### Are there GUIs for OpenSees?

OpenSees itself is command-line driven, but several third-party interfaces exist: STKO (Scientific ToolKit for OpenSees) provides a full pre/post-processing GUI, GiD+OpenSees offers commercial-grade meshing and visualization, and OpenSeesPy integrates with Jupyter notebooks for interactive analysis via Matplotlib visualizations.

### How do these tools handle uncertainty quantification?

All three incorporate uncertainty: OpenQuake uses logic trees for epistemic uncertainty in source models and GMPEs, OpenSees supports probabilistic modeling with random variables and Monte Carlo simulation, and OpenSHA implements the USGS's formalized logic tree approach for hazard model uncertainty.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Earthquake Engineering & Seismic Hazard Analysis: OpenSees vs OpenQuake vs OpenSHA",
  "description": "Comprehensive comparison of open-source earthquake engineering platforms: OpenSees for structural simulation, OpenQuake Engine for seismic hazard analysis, and OpenSHA for site-specific hazard curves. Includes Docker deployment, code examples, and integration workflows.",
  "datePublished": "2026-06-15",
  "dateModified": "2026-06-15",
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
