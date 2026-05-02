---
title: "Self-Hosted Model Registry & Model Versioning: MLflow vs ClearML vs DVC"
date: 2026-05-03T09:00:00Z
tags: ["ml-ops", "machine-learning", "model-registry", "model-versioning", "mlflow", "clearml", "dvc", "self-hosted"]
draft: false
---

As machine learning models move from experimental notebooks to production systems, managing model versions, tracking lineage, and controlling deployment stages becomes critical. A model registry provides a centralized store for model artifacts, metadata, and lifecycle management — from initial training through staging to production deployment.

While cloud providers offer managed model registries, self-hosted solutions give you complete control over model artifacts, avoid per-model storage fees, and keep sensitive models within your infrastructure. This guide compares three leading open-source model registry platforms: **MLflow Model Registry**, **ClearML Model Registry**, and **DVC (Data Version Control)**.

## What Is a Model Registry?

A model registry is a centralized system for managing the full lifecycle of machine learning models. Key capabilities include:

- **Versioning**: Track every model iteration with unique identifiers
- **Metadata storage**: Record training parameters, datasets, metrics, and code versions
- **Lifecycle stages**: Manage transitions from development to staging to production
- **Access control**: Control who can register, approve, or deploy models
- **Lineage tracking**: Trace which data and code produced each model version
- **Model serving integration**: Deploy registered models to inference endpoints

Self-hosted registries are essential for teams working with proprietary data, regulated industries, or those seeking to avoid vendor-specific model formats.

## MLflow Model Registry

MLflow is an open-source platform from Databricks that manages the complete ML lifecycle. Its Model Registry component provides versioning, lineage, stage management, and model serving capabilities.

### Architecture

MLflow consists of several components that can be self-hosted independently:

- **Tracking Server**: REST API and UI for logging experiments and registering models
- **Model Registry**: Centralized model store with versioned artifacts and stage transitions
- **Backend Store**: Metadata stored in PostgreSQL, MySQL, or SQLite
- **Artifact Store**: Model files stored on local filesystem, S3, GCS, or Azure Blob
- **Model Serving**: Built-in server for deploying registered models as REST endpoints

### Docker Compose Setup

```yaml
version: "3.8"
services:
  mlflow-tracking:
    image: ghcr.io/mlflow/mlflow:v2.19.0
    container_name: mlflow-server
    command: >
      mlflow server
      --host 0.0.0.0
      --port 5000
      --backend-store-uri mysql+pymysql://mlflow:mlflow_pass@mysql:3306/mlflow
      --default-artifact-root /mlartifacts
    ports:
      - "5000:5000"
    volumes:
      - mlflow_artifacts:/mlartifacts
    depends_on:
      mysql:
        condition: service_healthy
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    container_name: mlflow-mysql
    environment:
      MYSQL_ROOT_PASSWORD: root_pass
      MYSQL_DATABASE: mlflow
      MYSQL_USER: mlflow
      MYSQL_PASSWORD: mlflow_pass
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    container_name: mlflow-minio
    environment:
      MINIO_ROOT_USER: minio_admin
      MINIO_ROOT_PASSWORD: minio_secret
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"

volumes:
  mlflow_artifacts:
  mysql_data:
  minio_data:
```

### Registering and Managing Models

```python
import mlflow
from mlflow.tracking import MlflowClient

# Configure tracking server
mlflow.set_tracking_uri("http://localhost:5000")
client = MlflowClient(tracking_uri="http://localhost:5000")

# Log a model and register it
with mlflow.start_run():
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.datasets import load_breast_cancer

    X, y = load_breast_cancer(return_X_y=True)
    model = RandomForestClassifier(n_estimators=100)
    model.fit(X, y)

    mlflow.sklearn.log_model(model, "model")
    run_id = mlflow.active_run().info.run_id

# Register the model
model_uri = f"runs:/{run_id}/model"
result = mlflow.register_model(model_uri, "fraud-detection-model")
print(f"Registered model version: {result.version}")

# Transition to staging
client.transition_model_version_stage(
    name="fraud-detection-model",
    version=1,
    stage="Staging"
)

# Deploy the staging model
model = mlflow.sklearn.load_model(
    "models:/fraud-detection-model/Staging"
)
```

### Key Strengths

- Industry-standard ML lifecycle tool with the largest community
- Flavor-specific model saving (sklearn, TensorFlow, PyTorch, XGBoost, etc.)
- Built-in model serving with REST API and batch inference
- Rich UI for comparing runs, visualizing metrics, and managing model versions
- Extensive ecosystem of integrations with 50+ tools

## ClearML Model Registry

ClearML is an end-to-end MLOps platform that provides experiment tracking, orchestration, data management, and model registry in a single self-hosted solution. Its model registry integrates tightly with experiment tracking for full lineage visibility.

### Architecture

ClearML uses a server-based architecture with multiple components:

- **API Server**: REST API for all ClearML operations (Python/FastAPI)
- **Web App**: Single-page application for the dashboard
- **MongoDB**: Metadata and experiment tracking data
- **Elasticsearch**: Search and indexing for experiments and models
- **File Server**: Model artifact storage (or integrate with S3/GCS)

### Docker Compose Setup

```yaml
version: "3.8"
services:
  clearml-api:
    image: allegroai/clearml:latest
    container_name: clearml-api
    ports:
      - "8008:8008"
    environment:
      - CLEARML__apiserver__mongo__host=clearml-mongo
      - CLEARML__apiserver__elastic__host=clearml-elastic
    depends_on:
      - clearml-mongo
      - clearml-elastic
    restart: unless-stopped

  clearml-elastic:
    image: elasticsearch:7.17.0
    container_name: clearml-elastic
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - elastic_data:/usr/share/elasticsearch/data
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9200/_cluster/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 10

  clearml-mongo:
    image: mongo:6.0
    container_name: clearml-mongo
    volumes:
      - mongo_data:/data/db
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5

  clearml-web:
    image: allegroai/clearml:latest
    container_name: clearml-web
    ports:
      - "8080:80"
    environment:
      - CLEARML__apiserver__host=http://clearml-api:8008
    depends_on:
      - clearml-api
    restart: unless-stopped

  clearml-agent:
    image: allegroai/clearml-agent:latest
    container_name: clearml-agent
    environment:
      - CLEARML_API_SERVER=http://clearml-api:8008
      - CLEARML_WEB_SERVER=http://clearml-web:8080
      - CLEARML_FILES_SERVER=http://clearml-agent:8081
    ports:
      - "8081:8081"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    restart: unless-stopped

volumes:
  elastic_data:
  mongo_data:
```

### Using the Model Registry

```python
from clearml import Task, OutputModel

# Create a task (experiment)
task = Task.init(
    project_name="fraud-detection",
    task_name="random-forest-training",
    task_type=Task.TaskTypes.training
)

# Train and log model
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_breast_cancer

X, y = load_breast_cancer(return_X_y=True)
model = RandomForestClassifier(n_estimators=100)
model.fit(X, y)

# Register the model with ClearML
output_model = OutputModel()
output_model.update_weights(
    filename="fraud_model.pkl",
    auto_create_file=True,
    tags=["production", "v1"],
    comment="Initial fraud detection model"
)

# Query the model registry
from clearml import Model

# Get all models in a project
models = Model.query_models(project_name="fraud-detection")
for m in models:
    print(f"Model: {m.name}, Tags: {m.tags}, Created: {m.created}")

# Download a specific model version
model = Model.query_models(
    project_name="fraud-detection",
    tags=["production"]
)[0]
model.download("downloaded_model.pkl")
```

### Key Strengths

- Full MLOps platform in one self-hosted deployment (not just model registry)
- Automatic model capture from experiment runs — no manual registration needed
- Powerful web UI with experiment comparison, model visualization, and dataset versioning
- Built-in distributed training support with queue-based execution
- Model serving with automatic containerization and scaling

## DVC (Data Version Control)

DVC is an open-source tool for versioning datasets and ML models. Unlike MLflow and ClearML, DVC is not a full MLOps platform — it focuses on version control for data and models, integrating seamlessly with Git workflows.

### Architecture

DVC uses a Git-compatible approach:

- **.dvc files**: Lightweight text files stored in Git that track data/model locations
- **Remote Storage**: S3, GCS, Azure, SSH, or local filesystem for actual artifacts
- **Pipelines**: YAML-based pipeline definitions (dvc.yaml) for reproducible workflows
- **CLI-first**: All operations through the `dvc` command-line tool
- **DVC Studio**: Optional cloud dashboard (self-hosted option via DVC server is limited)

### Docker Compose Setup (Remote Storage)

DVC itself does not need a server. You configure a remote storage backend. Here is a self-hosted setup using MinIO as the S3-compatible remote:

```yaml
version: "3.8"
services:
  minio:
    image: minio/minio:latest
    container_name: dvc-minio
    environment:
      MINIO_ROOT_USER: dvc_admin
      MINIO_ROOT_PASSWORD: dvc_secret_key
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - dvc_storage:/data
    command: server /data --console-address ":9001"

  dvc-server:
    image: iterative/dvc:latest
    container_name: dvc-cli
    entrypoint: ["sleep", "infinity"]
    volumes:
      - ./project:/project
      - ./.dvc_cache:/root/.dvc/cache
    working_dir: /project

volumes:
  dvc_storage:
```

### Versioning Models with DVC

```bash
# Initialize DVC in your project
dvc init

# Configure MinIO as remote storage
dvc remote add -d myremote s3://models/
dvc remote modify myremote endpointurl http://localhost:9000
dvc remote modify myremote access_key_id dvc_admin
dvc remote modify myremote secret_access_key dvc_secret_key

# Track a model file
dvc add models/fraud_model_v1.pkl

# Commit to Git (the .dvc file goes to Git, the actual model goes to MinIO)
git add models/fraud_model_v1.pkl.dvc .dvc
git commit -m "Add fraud detection model v1"

# Push model artifact to remote storage
dvc push

# Create a DVC pipeline for reproducible training
cat > dvc.yaml << 'PIPELINE'
stages:
  train:
    cmd: python train.py
    deps:
      - data/training.csv
      - train.py
    outs:
      - models/fraud_model.pkl
      - metrics/accuracy.json
    metrics:
      - metrics/accuracy.json:
          cache: false
PIPELINE

# Run the pipeline
dvc repro
```

### Python API for Model Management

```python
import dvc.api

# Read data directly from a DVC-tracked remote
with dvc.api.open(
    "models/fraud_model_v1.pkl",
    remote="myremote",
    mode="rb"
) as f:
    import pickle
    model = pickle.load(f)

# Use DVC pipelines programmatically
from dvc.repo import Repo

repo = Repo()
repo.reproduce()  # Run the entire pipeline
```

### Key Strengths

- Git-native workflow — models versioned alongside code
- Extremely lightweight — no server infrastructure required (just storage backend)
- Excellent for data versioning alongside model versioning
- Works with any storage backend (S3, GCS, Azure, SSH, HDFS, HTTP)
- Pipeline definitions in simple YAML for reproducible experiments

## Comparison Table

| Feature | MLflow Model Registry | ClearML Model Registry | DVC |
|---------|----------------------|----------------------|-----|
| **Architecture** | Tracking server + DB | Full MLOps server | Git + remote storage |
| **Server Required** | Yes (Tracking Server) | Yes (API + Web + MongoDB) | No (CLI only) |
| **Storage Backend** | S3 / GCS / Azure / Local | Built-in or S3 / GCS | S3 / GCS / Azure / SSH / Any |
| **Model Versioning** | Automatic with runs | Automatic with experiments | Manual via `dvc add` |
| **Stage Management** | None, None, Production, Archived | Custom tags | Git branches/tags |
| **Model Serving** | Built-in REST server | Built-in with auto-containerization | Not built-in |
| **Experiment Tracking** | Built-in | Built-in (comprehensive) | Via DVC metrics |
| **Data Versioning** | No | Yes (datasets) | Yes (primary focus) |
| **Web UI** | Rich experiment + model UI | Full MLOps dashboard | Limited (DVC Studio) |
| **API** | REST + Python SDK | REST + Python SDK | CLI + Python API |
| **Infrastructure** | Medium (server + DB + storage) | High (server + MongoDB + ES) | Low (storage only) |
| **Best For** | Teams wanting standard ML registry | Teams wanting full MLOps platform | Teams wanting Git-native workflow |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| **GitHub Stars** | 18,000+ | 5,000+ | 13,000+ |

## Model Lifecycle Management

The three tools take fundamentally different approaches to model lifecycle:

**MLflow** uses a linear stage model (None → Staging → Production → Archived). You register a model from a run, transition it through stages, and load models by stage name. It is simple but limited — you cannot create custom stages or parallel production deployments.

**ClearML** uses a tag-based system that is more flexible. Models can have multiple tags (e.g., "production", "v2", "approved"), and you can query models by any combination of tags. This supports complex deployment workflows like canary releases or A/B testing.

**DVC** delegates lifecycle management to Git. Model versions are tracked through Git branches and tags. You might have a `models/production` branch, a `models/staging` branch, and use Git tags for specific releases. This integrates seamlessly with CI/CD pipelines but requires more manual coordination.

For related ML infrastructure topics, see our [ML pipeline orchestration comparison](../2026-05-03-self-hosted-ml-pipeline-orchestration-kubeflow-metaflow-zenml-guide/), [ML experiment tracking guide](../self-hosted-ml-experiment-tracking-mlflow-clearml-aim-guide-2026/), and [data versioning tools comparison](../dvc-lakefs-pachyderm-self-hosted-data-versioning-guide-2026/).

## Why Self-Host Your Model Registry?

**Data sovereignty**: Model artifacts often contain or are derived from sensitive data. Self-hosted registries ensure models never leave your infrastructure, which is critical for healthcare, finance, and government use cases.

**Cost savings at scale**: Managed model registries charge per stored model, per API call, and per deployment. Teams managing hundreds of model versions across multiple projects can save significantly by self-hosting on existing storage infrastructure.

**Custom integrations**: Self-hosted registries give you full API access. You can integrate with internal CI/CD systems, custom approval workflows, proprietary deployment targets, and internal authentication providers.

**No format lock-in**: Cloud model registries often require proprietary model formats. Self-hosted tools like MLflow and DVC support open model formats (ONNX, PMML, Pickle) that are portable across platforms.

## Choosing the Right Model Registry

- Choose **MLflow Model Registry** if you want the industry standard with the largest ecosystem, need built-in model serving, and prefer a dedicated tracking server with a polished web UI.

- Choose **ClearML Model Registry** if you want a complete self-hosted MLOps platform, need automatic model capture from experiments, and want the most powerful web UI for visualizing model lineage and experiment history.

- Choose **DVC** if you prefer a Git-native workflow, want the lightest possible infrastructure (just a storage backend), and need to version data alongside models for full reproducibility.

## FAQ

### Can I use MLflow Model Registry without Databricks?

Yes, absolutely. MLflow is fully open-source and can be self-hosted without any Databricks account or subscription. The tracking server, model registry, and model serving components all run independently. Databricks offers a managed version, but the open-source version has all the core features.

### Does DVC have a web interface like MLflow?

DVC is primarily a CLI tool and does not include a built-in web UI. DVC Studio (by Iterative, the company behind DVC) provides a web dashboard, but it is a cloud-hosted service. For a fully self-hosted web interface, MLflow or ClearML are better choices.

### How do these tools handle large model files?

All three tools support large model files through external storage backends. MLflow and ClearML store artifacts in S3, GCS, or Azure Blob Storage. DVC stores model files in any configured remote, including S3-compatible storage like MinIO. None of the tools store large files in the database — only metadata is stored in the backend store.

### Can I serve models directly from the registry?

MLflow has built-in model serving via `mlflow models serve`, which deploys a REST API for any registered model. ClearML includes model serving with automatic containerization and scaling. DVC does not include model serving — you would need to download the model and deploy it separately using your preferred serving framework.

### Which tool has the best Git integration?

DVC has the deepest Git integration by design — model tracking files (.dvc) live in your Git repository alongside your code, and model versions are managed through Git branches and tags. MLflow and ClearML track runs and models externally, though both can log Git commit information as metadata.

### Is it possible to use multiple tools together?

Yes. A common pattern is using DVC for data and model versioning (Git integration) alongside MLflow for experiment tracking and model registry. ZenML can orchestrate this by using DVC as the artifact store and MLflow as the experiment tracker. ClearML can also integrate with DVC for data versioning while using its own model registry.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Model Registry & Model Versioning: MLflow vs ClearML vs DVC",
  "description": "Compare three leading open-source model registry platforms for self-hosted deployment: MLflow, ClearML, and DVC. Includes Docker Compose configs, code examples, and feature comparison.",
  "datePublished": "2026-05-03",
  "dateModified": "2026-05-03",
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
