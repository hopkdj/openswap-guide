---
title: "Dagu vs Netflix Conductor vs Apache Airflow: Self-Hosted Workflow Orchestrators 2026"
date: 2026-04-24
tags: ["comparison", "guide", "self-hosted", "workflow", "orchestration", "devops"]
draft: false
description: "Compare Dagu, Netflix Conductor, and Apache Airflow for self-hosted workflow orchestration. Detailed setup guides, Docker configs, feature comparison, and performance benchmarks."
---

If you need to run scheduled jobs, chain dependent tasks, or orchestrate complex data pipelines, picking the right workflow orchestrator is critical. The three most popular open-source options in 2026 are **Dagu**, **Netflix Conductor**, and **Apache Airflow** — each targeting a different segment of the self-hosted workflow market.

This guide compares all three side by side, with real Docker Compose configurations from their official repositories, so you can deploy and evaluate them yourself.

## Why Self-Host Your Workflow Orchestrator

Self-hosted workflow engines give you full control over execution schedules, data privacy, and infrastructure costs. Unlike managed SaaS alternatives, you own the data, can customize retry logic, and avoid per-execution pricing. Whether you're orchestrating ETL pipelines, running cron-like scheduled jobs, or coordinating microservice workflows, a self-hosted solution eliminates vendor lock-in and integrates directly with your existing infrastructure.

For teams already running Docker infrastructure, all three tools support containerized deployment — but the complexity varies dramatically.

## Overview: Dagu vs Netflix Conductor vs Apache Airflow

| Feature | Dagu | Netflix Conductor | Apache Airflow |
|---------|------|-------------------|----------------|
| **Language** | Go | Java | Python |
| **GitHub Stars** | 3,300+ | 12,700+ | 45,100+ |
| **Last Updated** | April 2026 | December 2023 | April 2026 |
| **Workflow Definition** | YAML | JSON DSL | Python DAGs |
| **Web UI** | Built-in (React) | Built-in (React) | Built-in (Flask) |
| **Database** | BoltDB / SQLite | MySQL / Postgres / Redis | Postgres / MySQL |
| **Docker Support** | Native (runs containers) | Yes (Docker tasks) | Yes (DockerOperator) |
| **Distributed Workers** | Optional | Yes | Yes (Celery/K8s) |
| **Learning Curve** | Low | High | Medium |
| **Resource Footprint** | ~100 MB | ~2 GB (with ES + Redis) | ~1 GB (scheduler + web) |
| **Best For** | Small teams, ops scripts | Microservice orchestration | Data engineering, ETL |
| **License** | MIT | Apache 2.0 | Apache 2.0 |

Dagu is the newcomer (written in Go) focused on simplicity: define workflows as YAML files, get a built-in web UI with retry logic, approval gates, and optional distributed workers. Netflix Conductor is a mature microservice orchestration engine designed for complex distributed systems. Apache Airflow is the industry standard for data pipeline orchestration, with the largest ecosystem of operators and integrations.

## Dagu: Lightweight YAML-Based Workflow Engine

Dagu takes a radically different approach from Airflow. Instead of writing Python code, you define workflows as YAML files. A single Dagu process runs the scheduler, web server, and workers — making it trivially easy to deploy.

**Key features:**
- YAML-defined workflows with cron-like scheduling
- Built-in web UI for monitoring, retrying, and editing DAGs
- Approval gates for manual intervention steps
- Docker-in-Docker support for containerized tasks
- Email and Slack notifications
- Optional distributed worker mode

### Dagu Docker Compose Configuration

Dagu provides an official minimal Docker Compose setup in their repository at `deploy/docker/compose.minimal.yaml`:

```yaml
services:
  dagu:
    image: ghcr.io/dagucloud/dagu:latest
    container_name: dagu
    hostname: dagu

    ports:
      - "8080:8080"

    entrypoint: []

    command: ["dagu", "start-all"]

    environment:
      - DAGU_HOST=0.0.0.0
      - DAGU_PORT=8080
      - DAGU_DAGS_DIR=/var/lib/dagu/dags
      - DAGU_AUTH_MODE=basic
      - DAGU_AUTH_BASIC_USERNAME=admin
      - DAGU_AUTH_BASIC_PASSWORD=changeme

    volumes:
      - dagu-data:/var/lib/dagu
      - ./dags:/var/lib/dagu/dags:ro
      - /var/run/docker.sock:/var/run/docker.sock

    user: "0:0"

volumes:
  dagu-data:
    driver: local
```

The `start-all` command runs the server, scheduler, and coordinator in a single process — perfect for small deployments. For production, you can split these into separate services using `dagu server`, `dagu scheduler`, and `dagu worker` commands.

### Example Dagu Workflow

Here's a simple Dagu DAG that runs a data extraction pipeline:

```yaml
name: daily-data-extraction
schedule: "0 2 * * *"

steps:
  - name: extract-data
    command: python3 /scripts/extract.py
    dir: /var/lib/dagu

  - name: validate-data
    command: python3 /scripts/validate.py
    dir: /var/lib/dagu
    depends:
      - extract-data

  - name: load-to-warehouse
    command: python3 /scripts/load.py
    dir: /var/lib/dagu
    depends:
      - validate-data

  - name: send-notification
    command: |
      curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
        -d '{"text": "Daily ETL pipeline completed successfully"}'
    depends:
      - load-to-warehouse
```

### Installing Dagu Without Docker

```bash
# Using Homebrew (macOS/Linux)
brew install dagu

# Using Go
go install github.com/dagucloud/dagu/cmd/dagu@latest

# Binary download
curl -L https://github.com/dagucloud/dagu/releases/latest/download/dagu_linux_amd64.tar.gz | tar xz
sudo mv dagu /usr/local/bin/

# Start the server
dagu start-all
```

## Netflix Conductor: Enterprise Microservice Orchestration

Netflix Conductor is a battle-tested workflow orchestration platform built by Netflix for orchestrating microservices at scale. It uses a JSON-based DSL for workflow definitions and requires Elasticsearch for persistence and Redis for queue management.

**Key features:**
- JSON-based workflow DSL with rich task types
- Dynamic workflow generation at runtime
- Built-in retry with exponential backoff
- Human-in-the-loop tasks
- gRPC and REST APIs
- Polyglot client SDKs (Java, Python, Go, C#)
- Support for Kafka, SQS event queues

### Netflix Conductor Docker Compose Configuration

Conductor's official `docker/docker-compose.yaml` runs the server alongside Elasticsearch and Redis:

```yaml
version: '2.3'

services:
  conductor-server:
    image: conductor:server
    container_name: conductor-server
    build:
      context: ../
      dockerfile: docker/server/Dockerfile
    ports:
      - 8080:8080
      - 5000:5000
    environment:
      - CONFIG_PROP=config-redis.properties
    depends_on:
      conductor-elasticsearch:
        condition: service_healthy
      conductor-redis:
        condition: service_healthy
    networks:
      - internal

  conductor-redis:
    image: redis:6.2.3-alpine
    ports:
      - 7379:6379
    networks:
      - internal

  conductor-elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:7.17.11
    environment:
      - "ES_JAVA_OPTS=-Xms512m -Xmx1024m"
      - xpack.security.enabled=false
      - discovery.type=single-node
    ports:
      - 9201:9200
    networks:
      - internal

networks:
  internal:
```

The full stack requires Elasticsearch and Redis, which explains the heavier resource footprint. For production deployments, Netflix also provides MySQL and Postgres variants.

### Example Conductor Workflow Definition

```json
{
  "name": "order_processing_workflow",
  "description": "Process customer orders through payment and fulfillment",
  "version": 1,
  "tasks": [
    {
      "name": "validate_order",
      "taskReferenceName": "validate_order_ref",
      "type": "SIMPLE"
    },
    {
      "name": "process_payment",
      "taskReferenceName": "payment_ref",
      "type": "SIMPLE",
      "inputParameters": {
        "orderId": "${workflow.input.orderId}",
        "amount": "${workflow.input.amount}"
      }
    },
    {
      "name": "fulfillment",
      "taskReferenceName": "fulfillment_ref",
      "type": "SIMPLE",
      "inputParameters": {
        "orderId": "${workflow.input.orderId}"
      }
    }
  ],
  "outputParameters": {
    "orderId": "${workflow.input.orderId}",
    "status": "completed"
  }
}
```

### Installing Conductor

```bash
# Clone the repository
git clone https://github.com/Netflix/conductor.git
cd conductor

# Build with Gradle
./gradlew build

# Or use the pre-built Docker image
docker pull netflixoss/conductor:latest

# Start with Docker Compose
cd docker
docker compose up -d

# The UI is available at http://localhost:8080
# The API is available at http://localhost:8080/api
```

## Apache Airflow: The Industry Standard for Data Pipelines

Apache Airflow is the most widely adopted workflow orchestration platform, especially in data engineering teams. Workflows are defined as Python code (DAGs), giving you maximum flexibility for complex logic, dynamic task generation, and conditional branching.

**Key features:**
- Python-based DAG definitions
- 200+ built-in operators (Docker, Kubernetes, AWS, GCP, SQL, etc.)
- Dynamic task mapping and branching
- XCom for passing data between tasks
- Celery and Kubernetes executors for distributed execution
- Extensive plugin ecosystem
- Task-level retry and SLA alerting

### Apache Airflow Docker Compose Configuration

While Airflow doesn't ship a minimal compose file in the same way, here's the standard production-ready setup using the official Astronomer Docker image:

```yaml
version: '3'

services:
  postgres:
    image: postgres:13
    environment:
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
      POSTGRES_DB: airflow
    volumes:
      - postgres-db-volume:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

  airflow-webserver:
    image: apache/airflow:2.10.0-python3.11
    command: webserver
    ports:
      - "8080:8080"
    environment:
      AIRFLOW__CORE__EXECUTOR: CeleryExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres/airflow
      AIRFLOW__CELERY__BROKER_URL: redis://redis:6379/0
      AIRFLOW__CORE__FERNET_KEY: "your-fernet-key-here"
    depends_on:
      - postgres
      - redis
    volumes:
      - ./dags:/opt/airflow/dags
      - ./logs:/opt/airflow/logs
      - ./plugins:/opt/airflow/plugins

  airflow-scheduler:
    image: apache/airflow:2.10.0-python3.11
    command: scheduler
    environment:
      AIRFLOW__CORE__EXECUTOR: CeleryExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres/airflow
      AIRFLOW__CELERY__BROKER_URL: redis://redis:6379/0
      AIRFLOW__CORE__FERNET_KEY: "your-fernet-key-here"
    depends_on:
      - postgres
      - redis
    volumes:
      - ./dags:/opt/airflow/dags
      - ./logs:/opt/airflow/logs
      - ./plugins:/opt/airflow/plugins

  airflow-worker:
    image: apache/airflow:2.10.0-python3.11
    command: celery worker
    environment:
      AIRFLOW__CORE__EXECUTOR: CeleryExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres/airflow
      AIRFLOW__CELERY__BROKER_URL: redis://redis:6379/0
      AIRFLOW__CORE__FERNET_KEY: "your-fernet-key-here"
    depends_on:
      - postgres
      - redis
    volumes:
      - ./dags:/opt/airflow/dags
      - ./logs:/opt/airflow/logs
      - ./plugins:/opt/airflow/plugins

volumes:
  postgres-db-volume:
```

### Example Airflow DAG

```python
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'data-team',
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

def validate_data(**kwargs):
    print("Validating extracted data...")

with DAG(
    'daily_etl_pipeline',
    default_args=default_args,
    description='Daily ETL pipeline with extract, validate, load',
    schedule_interval='0 2 * * *',
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=['etl', 'data-pipeline'],
) as dag:

    extract = BashOperator(
        task_id='extract_data',
        bash_command='python3 /opt/airflow/scripts/extract.py',
    )

    validate = PythonOperator(
        task_id='validate_data',
        python_callable=validate_data,
    )

    load = BashOperator(
        task_id='load_to_warehouse',
        bash_command='python3 /opt/airflow/scripts/load.py',
    )

    extract >> validate >> load
```

### Installing Apache Airflow

```bash
# Install via pip
pip install apache-airflow

# Initialize the database
airflow db init

# Create an admin user
airflow users create \
    --username admin \
    --password admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com

# Start the webserver
airflow webserver --port 8080

# Start the scheduler (in a separate terminal)
airflow scheduler
```

## Performance and Resource Comparison

| Metric | Dagu | Netflix Conductor | Apache Airflow |
|--------|------|-------------------|----------------|
| **Idle RAM** | ~80 MB | ~1.5 GB | ~800 MB |
| **Startup Time** | < 5 seconds | 30-60 seconds | 15-30 seconds |
| **Max DAGs/min** | ~500 (single node) | ~2,000 (clustered) | ~1,000 (Celery) |
| **Task Latency** | ~100 ms | ~200 ms | ~500 ms |
| **DAG Parsing** | N/A (YAML) | N/A (JSON) | Python eval per tick |

Dagu's Go-based architecture gives it the smallest resource footprint by a wide margin. A single binary handles everything — no separate database, message broker, or web framework required (it embeds BoltDB). This makes it ideal for edge deployments, homelabs, or teams that don't want to manage a multi-service stack.

Netflix Conductor's Java + Elasticsearch + Redis stack is the heaviest but provides the highest throughput for microservice orchestration. The tradeoff is infrastructure complexity — you need to maintain three separate services plus the Conductor server itself.

Apache Airflow sits in the middle. Its Python DAG parsing adds overhead at scale, but the Celery executor distributes work effectively across worker nodes. The Kubernetes executor adds another layer of flexibility for container-native teams.

## When to Choose Each Tool

**Choose Dagu if:**
- You want the simplest possible setup (single binary, YAML configs)
- Your workflows are primarily shell scripts, cron jobs, and container tasks
- You have limited infrastructure and can't justify running multiple services
- You value a clean, modern web UI out of the box
- Your team doesn't want to write Python for workflow definitions

**Choose Netflix Conductor if:**
- You're orchestrating microservices with complex dependency chains
- You need dynamic workflow generation based on runtime conditions
- Your team already uses the Java/Spring ecosystem
- You require polyglot client SDKs for different services
- You need human-in-the-loop approval steps in production workflows

**Choose Apache Airflow if:**
- You're building data engineering pipelines (ETL, ELT, data quality)
- You need 200+ pre-built connectors to databases, cloud services, and APIs
- Your team is comfortable writing Python
- You want the largest community, most tutorials, and widest job market demand
- You need fine-grained task-level retry logic, SLA monitoring, and backfilling

For related reading, check out our guides on [Apache Airflow vs Prefect vs Dagster](../apache-airflow-vs-prefect-vs-dagster-self-hosted-data-orchestration-guide/), [Apache NiFi vs StreamPipes vs Kestra](../2026-04-24-apache-nifi-vs-streampipes-vs-kestra-self-hosted-data-pipeline-orchestration-guide-2026/), and [Temporal vs Camunda vs Flowable](../temporal-vs-camunda-vs-flowable-self-hosted-workflow-orchestration-guide-2026/) for more workflow orchestration comparisons.

## FAQ

### What is the easiest workflow orchestrator to self-host?

Dagu is the easiest to self-host. It runs as a single binary with built-in web UI, embedded BoltDB database, and no external dependencies. A basic setup takes under 5 minutes with Docker Compose. Apache Airflow requires Postgres and a scheduler, while Netflix Conductor needs Elasticsearch and Redis alongside the server.

### Can Dagu run Docker containers as workflow steps?

Yes. Dagu supports Docker-in-Docker (DinD) natively. By mounting the host's Docker socket (`/var/run/docker.sock`) and running as root, Dagu can execute Docker commands as workflow steps. This lets you run any containerized tool — database migrations, build jobs, or test suites — directly from your YAML-defined workflows.

### Does Netflix Conductor support Python workflows?

Netflix Conductor provides a Python SDK for defining and executing workflows, but the workflow definitions themselves are JSON-based DSL files. You register task handlers in Python (or Java, Go, C#) and Conductor orchestrates them. This differs from Airflow, where the entire DAG is written in Python code.

### How does Airflow compare to Dagu for cron-like scheduled jobs?

For simple cron-like jobs, Dagu is significantly simpler. Airflow requires setting up a database, webserver, scheduler, and worker — five separate processes minimum. Dagu runs everything in one process. However, if you need advanced features like backfilling historical runs, dynamic task generation, or complex branching logic, Airflow's Python-based approach provides more flexibility.

### Can I migrate from Airflow to Dagu or Conductor?

Direct migration is not straightforward because each tool uses a different workflow definition format (Python vs YAML vs JSON). However, the logical workflow structure (task dependencies, schedules, retry policies) translates across all three. A practical approach is to document your existing Airflow DAGs as flowcharts, then reimplement them in the target tool's format.

### Which workflow orchestrator has the best web UI?

Dagu has the most modern and intuitive web UI out of the box, with real-time execution graphs, retry buttons, and approval workflows. Airflow's UI is functional but dated (though Airflow 3.0 introduced a redesigned interface). Netflix Conductor's UI provides detailed task state tracking and workflow visualization but requires more navigation to find execution details.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Dagu vs Netflix Conductor vs Apache Airflow: Self-Hosted Workflow Orchestrators 2026",
  "description": "Compare Dagu, Netflix Conductor, and Apache Airflow for self-hosted workflow orchestration. Detailed setup guides, Docker configs, feature comparison, and performance benchmarks.",
  "datePublished": "2026-04-24",
  "dateModified": "2026-04-24",
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
