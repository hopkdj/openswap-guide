---
title: "Self-Hosted ML Pipeline Orchestration: Kubeflow Pipelines vs Metaflow vs ZenML"
date: 2026-05-03T08:00:00Z
tags: ["ml-ops", "machine-learning", "pipeline-orchestration", "kubeflow", "metaflow", "zenml", "docker", "self-hosted"]
draft: false
---

Machine learning projects quickly grow from simple notebooks into complex, multi-step workflows. Data preprocessing, feature engineering, model training, evaluation, and deployment all need to be orchestrated reliably, reproducibly, and at scale. While cloud providers offer managed ML pipeline services, self-hosted alternatives give you full control over your data, infrastructure, and costs.

This guide compares three leading open-source ML pipeline orchestration platforms — **Kubeflow Pipelines**, **Metaflow**, and **ZenML** — to help you choose the right tool for your self-hosted ML infrastructure.

## What Is ML Pipeline Orchestration?

ML pipeline orchestration automates the end-to-end machine learning workflow. Instead of manually running scripts in sequence, a pipeline orchestrator:

- Defines each step (data ingestion, preprocessing, training, evaluation) as a reusable component
- Manages dependencies between steps
- Tracks artifacts (datasets, models, metrics) across runs
- Enables versioning and reproducibility of entire workflows
- Scales execution across distributed compute resources

Self-hosted solutions are particularly valuable for organizations with strict data governance requirements, those operating in air-gapped environments, or teams looking to avoid vendor lock-in and cloud compute costs.

## Kubeflow Pipelines

Kubeflow Pipelines is a platform for building, deploying, and managing portable, scalable ML workflows on Kubernetes. Originally developed by Google, it is now a CNCF project with broad community support.

### Architecture

Kubeflow Pipelines runs on Kubernetes and consists of several components:

- **Pipeline DSL**: Python-based domain-specific language for defining workflows
- **Argo Workflows**: The underlying workflow engine that orchestrates container execution
- **ML Metadata**: Tracks artifacts and execution lineage
- **Persistent Volume Claims**: Stores pipeline outputs and model artifacts
- **API Server**: REST API for managing pipeline runs

### Docker Compose Setup (via Kind/Minikube)

Kubeflow requires Kubernetes, so it cannot run with a simple Docker Compose file. The recommended self-hosted deployment uses a local Kubernetes cluster:

```yaml
# Install Kubeflow Pipelines standalone on a local cluster
# First, create a kind cluster
kind create cluster --name kubeflow

# Then install KFP using the official manifests
kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/cluster-scoped-resources?ref=2.3.0"
kubectl wait --for condition=established --timeout=300s crd/applications.app.k8s.io
kubectl apply -k "github.com/kubeflow/pipelines/manifests/kustomize/env/platform-agnostic-pns?ref=2.3.0"
```

For production deployments, use the official Kubeflow deployment with Kustomize or Helm:

```yaml
# production-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-pipeline
  namespace: kubeflow
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ml-pipeline
  template:
    spec:
      containers:
      - name: ml-pipeline-api
        image: gcr.io/ml-pipeline/api-server:2.3.0
        ports:
        - containerPort: 8888
        env:
        - name: DBCONFIG_USER
          value: root
        - name: DBCONFIG_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-secret
              key: password
```

### Defining a Pipeline

```python
from kfp import dsl
from kfp.dsl import component

@component(base_image="python:3.11", packages_to_install=["pandas", "scikit-learn"])
def preprocess_data(input_path: str, output_path: str) -> str:
    import pandas as pd
    df = pd.read_csv(input_path)
    df = df.dropna()
    df.to_csv(output_path, index=False)
    return output_path

@component(base_image="python:3.11", packages_to_install=["scikit-learn"])
def train_model(train_path: str, model_path: str) -> float:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    import pandas as pd
    import joblib

    df = pd.read_csv(train_path)
    X, y = df.drop("target", axis=1), df["target"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    model = RandomForestClassifier(n_estimators=100)
    model.fit(X_train, y_train)
    accuracy = model.score(X_test, y_test)

    joblib.dump(model, model_path)
    return accuracy

@dsl.pipeline(name="ml-training-pipeline", description="End-to-end ML training")
def training_pipeline(data_path: str):
    preprocess_step = preprocess_data(input_path=data_path, output_path="/data/cleaned.csv")
    train_step = train_model(
        train_path=preprocess_step.output,
        model_path="/models/model.pkl"
    )
    train_step.after(preprocess_step)
```

### Key Strengths

- Runs natively on Kubernetes with full scalability
- Rich web UI for visualizing pipeline runs and comparing experiments
- Strong artifact tracking and lineage via ML Metadata
- Supports Python, container-based, and custom component types
- Active CNCF project with large community and enterprise adoption

## Metaflow

Metaflow is an open-source framework developed by Netflix that makes it easy to build and manage real-life data science and ML pipelines. Unlike Kubeflow, Metaflow is framework-agnostic and can run locally, on AWS Batch, or on Kubernetes.

### Architecture

Metaflow uses a Python decorator-based approach to define workflows:

- **Flow Spec**: Python class decorated with `@step` to define pipeline steps
- **Metadata Service**: Tracks runs, artifacts, and parameters (self-hosted via PostgreSQL)
- **Datastore**: Stores artifacts locally, on S3, or on Azure Blob Storage
- **Scheduler**: Integrates with cron, AWS EventBridge, or Kubernetes CronJob for scheduling

### Docker Compose Setup

Metaflow's self-hosted metadata service runs with PostgreSQL:

```yaml
version: "3.8"
services:
  metaflow-metadata:
    image: postgres:15-alpine
    container_name: metaflow-postgres
    environment:
      POSTGRES_DB: metaflow
      POSTGRES_USER: metaflow_user
      POSTGRES_PASSWORD: metaflow_secret
    ports:
      - "5432:5432"
    volumes:
      - metaflow_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U metaflow_user -d metaflow"]
      interval: 10s
      timeout: 5s
      retries: 5

  metaflow-service:
    image: ghcr.io/outerbounds/metaflow-service:latest
    container_name: metaflow-service
    environment:
      MF_DB_PORT_5432_TCP_ADDR: metaflow-postgres
      MF_DB_PORT_5432_TCP_PORT: "5432"
      MF_METADATA_DB_USER: metaflow_user
      MF_METADATA_DB_PSWD: metaflow_secret
      MF_METADATA_DB_NAME: metaflow
    ports:
      - "8083:8083"
    depends_on:
      metaflow-metadata:
        condition: service_healthy
    restart: unless-stopped

volumes:
  metaflow_data:
```

### Defining a Flow

```python
from metaflow import FlowSpec, step, Parameter, IncludeFile

class TrainingFlow(FlowSpec):
    data_file = IncludeFile(
        "data",
        is_text=True,
        help="CSV data file for training",
        default="training_data.csv"
    )

    n_estimators = Parameter(
        "n_estimators",
        help="Number of trees in the forest",
        default=100
    )

    @step
    def start(self):
        import pandas as pd
        self.df = pd.read_csv(self.data_file)
        self.next(self.preprocess)

    @step
    def preprocess(self):
        self.df = self.df.dropna()
        self.features = self.df.drop("target", axis=1)
        self.labels = self.df["target"]
        self.next(self.train)

    @step
    def train(self):
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        import joblib

        X_train, X_test, y_train, y_test = train_test_split(
            self.features, self.labels, test_size=0.2
        )

        self.model = RandomForestClassifier(
            n_estimators=self.n_estimators
        )
        self.model.fit(X_train, y_train)
        self.accuracy = self.model.score(X_test, y_test)
        joblib.dump(self.model, "model.pkl")

        self.next(self.end)

    @step
    def end(self):
        print(f"Training complete. Accuracy: {self.accuracy:.4f}")

if __name__ == "__main__":
    TrainingFlow()
```

### Key Strengths

- Simple Python decorator syntax — feels like writing normal Python code
- Runs locally for development, scales to Kubernetes or AWS Batch for production
- Excellent debugging and replay capabilities (resume from any failed step)
- Built-in parameter management and versioning
- Lower infrastructure overhead than Kubeflow (no Kubernetes required for local runs)

## ZenML

ZenML is an extensible, open-source MLOps framework that lets data scientists build portable ML pipelines using their preferred tools. It abstracts away the infrastructure layer, allowing you to swap orchestrators, artifact stores, and model registries without changing pipeline code.

### Architecture

ZenML uses a stack-based architecture:

- **Stack**: A combination of components (orchestrator, artifact store, experiment tracker, etc.)
- **Orchestrator**: Runs the pipeline steps (local, Kubernetes, Airflow, etc.)
- **Artifact Store**: Stores pipeline outputs (local filesystem, S3, GCS)
- **Metadata Store**: Tracks pipeline runs and metadata (SQLite, MySQL, PostgreSQL)
- **Integrations**: Plugins for 40+ tools (MLflow, Kubeflow, TensorFlow, etc.)

### Docker Compose Setup

ZenML server with MySQL metadata storage:

```yaml
version: "3.8"
services:
  zenml-server:
    image: zenmldocker/zenml-server:latest
    container_name: zenml-server
    environment:
      ZENML_STORE_URL: mysql://zenml:zenml_password@mysql:3306/zenml_db
    ports:
      - "8237:8237"
    depends_on:
      mysql:
        condition: service_healthy
    restart: unless-stopped

  mysql:
    image: mysql:8.0
    container_name: zenml-mysql
    environment:
      MYSQL_ROOT_PASSWORD: root_password
      MYSQL_DATABASE: zenml_db
      MYSQL_USER: zenml
      MYSQL_PASSWORD: zenml_password
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  mysql_data:
```

### Defining a Pipeline

```python
from zenml import pipeline, step
from zenml.client import Client

@step
def load_data() -> tuple:
    import pandas as pd
    from sklearn.datasets import load_breast_cancer

    data = load_breast_cancer()
    df = pd.DataFrame(data.data, columns=data.feature_names)
    df["target"] = data.target
    return df

@step
def train_model(df: tuple, n_estimators: int = 100) -> dict:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    import joblib

    X = df.drop("target", axis=1)
    y = df["target"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    model = RandomForestClassifier(n_estimators=n_estimators)
    model.fit(X_train, y_train)
    accuracy = model.score(X_test, y_test)

    joblib.dump(model, "model.pkl")
    return {"accuracy": accuracy, "model_path": "model.pkl"}

@step
def evaluate_model(results: dict) -> None:
    print(f"Model accuracy: {results['accuracy']:.4f}")
    assert results["accuracy"] > 0.9, "Model accuracy below threshold"

@pipeline
def training_pipeline(n_estimators: int = 100):
    df = load_data()
    results = train_model(df, n_estimators=n_estimators)
    evaluate_model(results)

if __name__ == "__main__":
    training_pipeline(n_estimators=200)
```

### Key Strengths

- Stack-based architecture — swap infrastructure without changing pipeline code
- 40+ integrations with popular ML tools (MLflow, Kubeflow, TensorFlow, PyTorch)
- Simple, clean Python API with decorators
- Supports local development and production Kubernetes deployment
- Built-in experiment tracking and model registry integrations

## Comparison Table

| Feature | Kubeflow Pipelines | Metaflow | ZenML |
|---------|-------------------|----------|-------|
| **Primary Orchestrator** | Argo Workflows (Kubernetes) | Local/AWS Batch/K8s | Local/K8s/Airflow |
| **Kubernetes Required** | Yes (mandatory) | No (optional) | No (optional) |
| **Infrastructure Overhead** | High (full K8s cluster) | Low (local dev) | Medium (server + DB) |
| **Python API** | DSL + decorators | Class-based decorators | Function decorators |
| **Artifact Storage** | Kubernetes PVCs / S3 | Local / S3 / Azure | Local / S3 / GCS |
| **Metadata Tracking** | ML Metadata | PostgreSQL | SQLite / MySQL / PostgreSQL |
| **Web UI** | Rich built-in UI | Basic metadata UI | ZenML Dashboard |
| **Reproducibility** | Container versioning | Built-in step caching | Step-level caching |
| **Extensibility** | Custom container components | Custom decorators | 40+ stack integrations |
| **Learning Curve** | Steep (K8s knowledge) | Gentle (Python native) | Moderate |
| **Best For** | Enterprise K8s environments | Data science teams | MLOps teams wanting flexibility |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| **GitHub Stars** | 16,000+ | 4,500+ | 5,000+ |

## Deployment Complexity

When choosing a self-hosted ML pipeline tool, deployment complexity is often the deciding factor:

- **Kubeflow Pipelines** requires a fully operational Kubernetes cluster. This means managing control plane, node pools, storage classes, and ingress configuration. It is the most powerful option but also the most infrastructure-heavy. Use it when you already have Kubernetes expertise and need enterprise-scale orchestration.

- **Metaflow** can run entirely on a laptop during development, then scale to Kubernetes or AWS Batch for production. The self-hosted metadata service requires only PostgreSQL. This makes it ideal for teams that want to iterate quickly without managing complex infrastructure.

- **ZenML** sits in the middle. The ZenML server plus a MySQL database is straightforward to deploy with Docker Compose, and pipelines can run locally or on Kubernetes depending on your stack configuration. Its abstraction layer means you can start simple and scale up without rewriting pipeline code.

## Integration Ecosystem

Each platform has a different approach to integrating with the broader ML toolchain:

**Kubeflow** is designed as a complete ML platform. It includes or integrates with KServe for model serving, Katib for hyperparameter tuning, and the Model Registry for model lifecycle management. It works best when you want an all-in-one Kubernetes-native ML stack.

**Metaflow** focuses on the pipeline orchestration layer and integrates with external tools for other ML lifecycle stages. It works well with MLflow for experiment tracking, SageMaker for training, and your existing data warehouse.

**ZenML** is designed specifically for integration. Its stack concept lets you combine any orchestrator with any artifact store, any experiment tracker, and any model registry. Want to use Kubeflow as the orchestrator, MLflow for tracking, and S3 for artifacts? That is a single stack configuration in ZenML.

For related ML infrastructure topics, see our [ML experiment tracking guide](../self-hosted-ml-experiment-tracking-mlflow-clearml-aim-guide-2026/), [ML feature store comparison](../feast-vs-featureform-vs-hopsworks-self-hosted-ml-feature-store-2026/), and [Kubernetes management platforms](../2026-04-22-rancher-vs-kubespray-vs-kind-self-hosted-kubernetes-management-guide-/).

## Why Self-Host Your ML Pipelines?

Running ML pipeline orchestration on your own infrastructure offers several compelling advantages over managed cloud services:

**Data sovereignty and compliance**: Many industries — healthcare, finance, government — have strict requirements about where data can be processed. Self-hosted pipelines keep all data processing within your network perimeter, simplifying compliance with GDPR, HIPAA, and other regulations.

**Cost control at scale**: Cloud ML services charge per pipeline run, per GB of artifact storage, and per compute hour. For teams running thousands of experiments, these costs add up quickly. Self-hosted solutions let you use existing compute infrastructure and scale horizontally with commodity hardware.

**No vendor lock-in**: Managed ML services tie you to a specific cloud provider's ecosystem. Self-hosted tools are portable — you can migrate from on-premise to cloud or between cloud providers without rewriting your pipelines.

**Custom integrations**: Self-hosted deployments give you full access to the database, API, and configuration. You can integrate with internal authentication systems, custom artifact stores, or proprietary data sources that managed services do not support.

## Choosing the Right Tool

The best choice depends on your team's specific needs:

- Choose **Kubeflow Pipelines** if you already run Kubernetes at scale, need a complete ML platform with built-in model serving and hyperparameter tuning, and have the infrastructure expertise to manage it.

- Choose **Metaflow** if you want the simplest developer experience, need to iterate quickly on a laptop before scaling to production, and prefer a Python-native approach over infrastructure configuration.

- Choose **ZenML** if you want flexibility to swap infrastructure components, need integrations with many different ML tools, and prefer a clean abstraction layer that keeps your pipeline code independent of your deployment target.

## FAQ

### Is Kubeflow Pipelines free to use?

Yes, Kubeflow Pipelines is open-source under the Apache 2.0 license and is a CNCF project. There are no licensing fees. However, the infrastructure cost of running a Kubernetes cluster can be significant. You can reduce costs by using a managed Kubernetes service or running on-premise with commodity hardware.

### Can Metaflow run without AWS?

Yes, Metaflow can run entirely locally on your development machine. For production, it supports self-hosted Kubernetes (via the Metaflow Kubernetes Service) or AWS Batch. The metadata service runs on PostgreSQL, which you can host anywhere. No AWS services are required.

### How does ZenML differ from Airflow?

ZenML is purpose-built for ML workflows, while Airflow is a general-purpose task orchestrator. ZenML provides ML-specific features like built-in artifact versioning, experiment tracking integration, model registry support, and type-aware data passing between steps. Airflow can be used as a ZenML orchestrator backend, giving you the best of both worlds.

### Do these tools support GPU workloads?

All three platforms support GPU workloads. Kubeflow Pipelines can request GPU resources through Kubernetes device plugins. Metaflow supports GPU instances on AWS Batch and Kubernetes. ZenML can use any GPU-capable orchestrator backend, including local GPUs for development and cloud GPUs for production training runs.

### Can I migrate between these platforms?

Migration is easiest with ZenML, since its abstraction layer separates pipeline code from infrastructure. You can switch orchestrators by changing your stack configuration. Kubeflow and Metaflow use different DSLs, so migration would require rewriting pipeline definitions. However, all three produce standard artifacts (models, datasets) that are portable.

### What is the minimum hardware requirement for self-hosting?

Metaflow can run on a single laptop with 8 GB RAM. ZenML requires a server with 4 GB RAM for the metadata server plus database. Kubeflow Pipelines requires a Kubernetes cluster — the minimum practical deployment is 3 nodes with 16 GB RAM each, though production deployments should use more resources.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted ML Pipeline Orchestration: Kubeflow Pipelines vs Metaflow vs ZenML",
  "description": "Compare three leading open-source ML pipeline orchestration platforms for self-hosted deployment: Kubeflow Pipelines, Metaflow, and ZenML. Includes Docker Compose configs, code examples, and a detailed feature comparison.",
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
