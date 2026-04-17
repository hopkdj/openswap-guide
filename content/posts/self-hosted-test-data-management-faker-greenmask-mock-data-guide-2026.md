---
title: "Self-Hosted Test Data Management: Faker, Greenmask & Mock Data Tools 2026"
date: 2026-04-17
tags: ["comparison", "guide", "self-hosted", "privacy", "testing"]
draft: false
description: "Complete guide to self-hosted test data management in 2026 — generate realistic, privacy-safe test data with Faker, Greenmask, data masking tools, and synthetic data generators."
---

Generating realistic test data without exposing production secrets is one of the most common challenges engineering teams face. Whether you need sample data for local development, anonymized datasets for staging environments, or synthetic data for compliance testing, self-hosted test data management tools give you full control over how data is created, transformed, and stored.

This guide covers the best open-source, self-hosted test data management tools available in 2026 — including Faker for synthetic generation, Greenmask for PostgreSQL data masking, and several practical approaches to building your own test data pipeline.

## Why Self-Host Test Data Management?

Using production data in non-production environments creates serious risks:

- **Privacy violations** — GDPR, HIPAA, and SOC 2 all restrict how personal data can be copied and stored
- **Security exposure** — every environment holding real data expands your attack surface
- **Compliance failures** — auditors routinely flag unmasked production data in staging
- **Cost overhead** — managed data masking services from major vendors charge per-row or per-seat pricing that scales unpredictably

Self-hosted test data generation and masking tools solve these problems by keeping data transformation entirely within your infrastructure. You generate synthetic data locally, mask production dumps before they leave your network, and build repeatable data pipelines that work the same way on a developer's laptop as they do in CI/CD.

### The Three Pillars of Test Data Management

1. **Synthetic data generation** — create entirely fake data that mimics real-world distributions and relationships
2. **Data masking and anonymization** — take production data and strip or replace sensitive fields
3. **Data subsetting** — extract a small, representative slice of production data for testing purposes

The tools below cover all three pillars, and most teams benefit from combining at least two of them.

## Faker: The Universal Synthetic Data Generator

[Faker](https://github.com/joke2k/faker) is the most widely used open-source library for generating fake data. Despite the name similarity with the PHP project, the Python Faker library has become the de facto standard for test data generation across dozens of languages through community ports.

### Key Features

- **40+ built-in providers** — names, addresses, phone numbers, emails, dates, companies, lorem ipsum, and much more
- **Locale support** — generate culturally appropriate data for 60+ locales (en_US, zh_CN, de_DE, ja_JP, etc.)
- **Deterministic output** — seed the generator for reproducible test data across test runs
- **Extensible architecture** — write custom providers for domain-specific data types

### Installation

```bash
pip install Faker
```

### Basic Usage

```python
from faker import Faker

fake = Faker()

# Generate individual values
print(fake.name())          # "Sarah Mitchell"
print(fake.email())         # "johnson.kyle@example.com"
print(fake.address())       # "4562 Johnson Park\nSouth James, CO 89432"
print(fake.company())       # "Thompson-Williams LLC"
print(fake.date_between())  # "2024-03-15"

# Deterministic generation with seeds
fake_seeded = Faker(seed=42)
print(fake_seeded.name())   # Always "Bailey Rodriguez" with seed 42
```

### Generating Bulk Test Data as CSV

For most testing scenarios, you need structured datasets, not individual values. Here's a practical script that generates a complete customer database as CSV:

```python
import csv
from faker import Faker
from datetime import datetime, timedelta
import random

fake = Faker('en_US')

NUM_RECORDS = 10_000
OUTPUT_FILE = 'test_customers.csv'

with open(OUTPUT_FILE, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow([
        'customer_id', 'first_name', 'last_name', 'email',
        'phone', 'street', 'city', 'state', 'zip',
        'signup_date', 'total_orders', 'lifetime_value'
    ])

    for i in range(1, NUM_RECORDS + 1):
        signup = fake.date_between(start_date='-730d', end_date='today')
        orders = random.randint(0, 50)
        ltv = round(random.uniform(0, 5000) * (orders / 5 + 0.2), 2)

        writer.writerow([
            f'CUST-{i:06d}',
            fake.first_name(),
            fake.last_name(),
            fake.email(),
            fake.phone_number(),
            fake.street_address(),
            fake.city(),
            fake.state_abbr(),
            fake.zipcode(),
            signup.isoformat(),
            orders,
            ltv
        ])

print(f"Generated {NUM_RECORDS} records → {OUTPUT_FILE}")
```

This produces a realistic 10,000-row dataset with correlated fields (higher order counts correlate with higher lifetime values) in under 2 seconds on a typical laptop.

### Loading into PostgreSQL

```bash
# Create the table
psql -U postgres -d testdb -c "
CREATE TABLE customers (
    customer_id VARCHAR(20) PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(30),
    street VARCHAR(255),
    city VARCHAR(100),
    state CHAR(2),
    zip VARCHAR(10),
    signup_date DATE,
    total_orders INTEGER,
    lifetime_value DECIMAL(10,2)
);"

# Import the CSV
psql -U postgres -d testdb -c "
COPY customers FROM '/path/to/test_customers.csv'
WITH (FORMAT csv, HEADER true);"
```

### Custom Providers for Domain-Specific Data

The real power of Faker emerges when you define custom providers that match your domain:

```python
from faker import Faker
from faker.providers import BaseProvider
import random

class ProductProvider(BaseProvider):
    def product_sku(self) -> str:
        prefix = random.choice(['WDG', 'APP', 'SRV', 'LIC'])
        return f"{prefix}-{random.randint(10000, 99999)}"

    def product_name(self) -> str:
        nouns = ['Widget', 'Module', 'Connector', 'Pipeline', 'Agent']
        adjectives = ['Advanced', 'Smart', 'Cloud', 'Pro', 'Lite']
        return f"{random.choice(adjectives)} {random.choice(nouns)}"

    def price(self, min_val: float = 9.99, max_val: float = 999.99) -> float:
        return round(random.uniform(min_val, max_val), 2)

fake = Faker()
fake.add_provider(ProductProvider)

print(fake.product_sku())     # "WDG-42817"
print(fake.product_name())    # "Cloud Connector"
print(fake.price())           # 247.83
```

## Greenmask: PostgreSQL Data Masking and Anonymization

While Faker generates synthetic data from scratch, [Greenmask](https://github.com/GreenmaskIO/greenmask) takes a different approach: it takes real production data and transforms it to remove sensitive information while preserving data structure, relationships, and distributions. This is invaluable when you need test data that matches production characteristics exactly.

### Key Features

- **PostgreSQL-native** — works directly with pg_dump/pg_restore pipelines
- **30+ built-in transformers** — masking for emails, phones, names, addresses, credit cards, and more
- **Referential integrity** — maintains foreign key relationships across tables during transformation
- **Declarative configuration** — YAML-based config files that are version-controlled alongside your code
- **Pipeline architecture** — chain multiple transformers on a single column

### Installation

Greenmask is distributed as a single Go binary:

```bash
# Download the latest release
curl -sL https://github.com/GreenmaskIO/greenmask/releases/latest/download/greenmask-linux-amd64 \
  -o /usr/local/bin/greenmask
chmod +x /usr/local/bin/greenmask

# Verify
greenmask --version
```

### Configuration

Create a `greenmask.yaml` configuration file:

```yaml
dump:
  pg_dump_path: pg_dump
  pg_restore_path: pg_restore
  connection:
    host: prod-db.internal
    port: 5432
    user: greenmask_reader
    password: "${DB_PASSWORD}"
    dbname: production

storage:
  type: directory
  path: /tmp/greenmask-output

transformations:
  - schema: public
    name: users
    transformers:
      - name: RandomUuid
        params:
          column: id
      - name: RandomEmail
        params:
          column: email
          domain: example.com
      - name: RandomString
        params:
          column: name
          min: 5
          max: 20
          type: name
      - name: RandomPhone
        params:
          column: phone
      - name: RandomDate
        params:
          column: created_at
          min: "2020-01-01"
          max: "2026-12-31"

  - schema: public
    name: orders
    transformers:
      - name: RandomUuid
        params:
          column: id
      - name: RandomUuid
        params:
          column: user_id
          keep_referential_integrity: true  # Preserves FK links to users table
      - name: RandomFloat
        params:
          column: total_amount
          min: 5.00
          max: 500.00
```

The `keep_referential_integrity: true` flag is critical — it ensures that the masked `user_id` in the orders table still correctly references the corresponding masked user in the users table.

### Running a Masked Dump

```bash
# Set environment variables
export DB_PASSWORD="your-prod-password"

# Run the masked dump and restore to local database
greenmask --config greenmask.yaml dump restore \
  --pg-connection "host=localhost port=5432 user=test dbname=staging"

# Or dump to a file for later use
greenmask --config greenmask.yaml dump create \
  --output-path /backups/staging-masked-$(date +%Y%m%d).dump
```

### Available Transformers

Greenmask ships with a comprehensive set of transformers out of the box:

| Transformer | Use Case | Example Output |
|---|---|---|
| `RandomUuid` | Replace UUIDs | `a3f1b2c4-...` |
| `RandomEmail` | Mask email addresses | `xk7d2m@example.com` |
| `RandomPhone` | Mask phone numbers | `+1-555-014-8832` |
| `RandomString` | Mask names/text | `Jk4mPqR7` |
| `RandomDate` | Shift or replace dates | `2023-07-14` |
| `RandomFloat` | Mask monetary values | `127.45` |
| `Hash` | Hash column values | `sha256:...` |
| `Masking` | Partial masking | `j***n@example.com` |
| `Template` | Custom expression | `{{FirstName}}_{{LastName}}` |
| `Replace` | Value substitution | `REDACTED` |

### Advanced: Column Validation

Greenmask includes a validation system to verify that transformations completed successfully:

```yaml
validation:
  - schema: public
    name: users
    checks:
      - name: no_null_emails
        query: "SELECT COUNT(*) FROM users WHERE email IS NULL"
        expected: 0
      - name: valid_email_format
        query: "SELECT COUNT(*) FROM users WHERE email !~ '^[^@]+@[^@]+\\.[^@]+$'"
        expected: 0
      - name: referential_integrity
        query: |
          SELECT COUNT(*) FROM orders o
          LEFT JOIN users u ON o.user_id = u.id
          WHERE u.id IS NULL
        expected: 0
```

## Building a Complete Test Data Pipeline

The most effective approach combines synthetic generation with production masking. Here's a practical pipeline architecture that works for most teams:

### Architecture Overview

```
Production DB ──┬──> Greenmask (mask) ──> Staging DB
                │
                └──> Schema extraction ──> Faker (generate) ──> Dev/Test DB
```

### Docker Compose Setup

Run the entire test data infrastructure locally:

```yaml
version: "3.9"

services:
  # Fresh PostgreSQL for test data
  test-db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: testdb
      POSTGRES_USER: testuser
      POSTGRES_PASSWORD: testpass
    ports:
      - "5432:5432"
    volumes:
      - test_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U testuser -d testdb"]
      interval: 5s
      timeout: 3s
      retries: 5

  # Faker data generator (runs once, then exits)
  data-generator:
    build: ./data-generator
    environment:
      DB_HOST: test-db
      DB_PORT: 5432
      DB_NAME: testdb
      DB_USER: testuser
      DB_PASSWORD: testpass
      NUM_RECORDS: 50000
    depends_on:
      test-db:
        condition: service_healthy

  # pgAdmin for inspecting generated data
  pgadmin:
    image: dpage/pgadmin4:latest
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@local.dev
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"
    depends_on:
      - test-db

volumes:
  test_data:
```

### The Generator Service

Here's a Dockerfile and entrypoint script for the data generator:

```dockerfile
# data-generator/Dockerfile
FROM python:3.12-slim

RUN pip install Faker psycopg2-binary

COPY generate.py /app/generate.py
WORKDIR /app

CMD ["python", "generate.py"]
```

```python
# data-generator/generate.py
import os
import psycopg2
from faker import Faker
import random
from datetime import datetime, timedelta

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'dbname': os.getenv('DB_NAME', 'testdb'),
    'user': os.getenv('DB_USER', 'testuser'),
    'password': os.getenv('DB_PASSWORD', 'testpass'),
}

NUM_RECORDS = int(os.getenv('NUM_RECORDS', '10000'))

fake = Faker()
fake.seed_instance(42)  # Reproducible across runs

def generate_schema(conn):
    """Create tables with realistic schema."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                budget DECIMAL(12,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS employees (
                id SERIAL PRIMARY KEY,
                department_id INTEGER REFERENCES departments(id),
                first_name VARCHAR(50) NOT NULL,
                last_name VARCHAR(50) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                phone VARCHAR(20),
                hire_date DATE NOT NULL,
                salary DECIMAL(10,2) NOT NULL,
                is_active BOOLEAN DEFAULT true
            );

            CREATE TABLE IF NOT EXISTS projects (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                department_id INTEGER REFERENCES departments(id),
                start_date DATE,
                end_date DATE,
                status VARCHAR(20) DEFAULT 'planning',
                budget DECIMAL(12,2)
            );

            CREATE TABLE IF NOT EXISTS assignments (
                id SERIAL PRIMARY KEY,
                employee_id INTEGER REFERENCES employees(id),
                project_id INTEGER REFERENCES projects(id),
                role VARCHAR(50),
                hours_allocated INTEGER DEFAULT 0
            );

            CREATE INDEX idx_emp_dept ON employees(department_id);
            CREATE INDEX idx_emp_email ON employees(email);
            CREATE INDEX idx_proj_dept ON projects(department_id);
            CREATE INDEX idx_assign_emp ON assignments(employee_id);
        """)
    conn.commit()

def generate_departments(conn, count=20):
    departments = []
    with conn.cursor() as cur:
        for i in range(count):
            name = fake.company() + " " + random.choice([
                'Engineering', 'Marketing', 'Sales', 'Operations',
                'Research', 'Support', 'Finance', 'Legal'
            ])
            budget = round(random.uniform(50000, 2000000), 2)
            cur.execute(
                "INSERT INTO departments (name, budget) VALUES (%s, %s) RETURNING id",
                (name, budget)
            )
            departments.append(cur.fetchone()[0])
    conn.commit()
    return departments

def generate_employees(conn, dept_ids, count=1000):
    employees = []
    with conn.cursor() as cur:
        for i in range(count):
            dept = random.choice(dept_ids)
            salary = round(random.uniform(40000, 180000), 2)
            hire = fake.date_between(start_date='-3650d', end_date='-30d')
            cur.execute("""
                INSERT INTO employees (department_id, first_name, last_name, email, phone, hire_date, salary)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (
                dept, fake.first_name(), fake.last_name(), fake.email(),
                fake.phone_number(), hire, salary
            ))
            employees.append(cur.fetchone()[0])

            # Batch commit every 500 records
            if i % 500 == 499:
                conn.commit()
    conn.commit()
    return employees

def generate_projects(conn, dept_ids, count=100):
    statuses = ['planning', 'active', 'completed', 'on_hold', 'cancelled']
    with conn.cursor() as cur:
        for _ in range(count):
            dept = random.choice(dept_ids)
            start = fake.date_between(start_date='-730d', end_date='-30d')
            end = fake.date_between(start_date=start, end_date='+365d')
            budget = round(random.uniform(10000, 500000), 2)
            cur.execute("""
                INSERT INTO projects (name, department_id, start_date, end_date, status, budget)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (fake.catch_phrase(), dept, start, end, random.choice(statuses), budget))
    conn.commit()

def generate_assignments(conn, emp_count, proj_count):
    roles = ['lead', 'contributor', 'reviewer', 'observer', 'coordinator']
    with conn.cursor() as cur:
        for _ in range(emp_count * 2):  # Avg 2 projects per employee
            emp_id = random.randint(1, emp_count)
            proj_id = random.randint(1, proj_count)
            hours = random.randint(4, 40)
            cur.execute("""
                INSERT INTO assignments (employee_id, project_id, role, hours_allocated)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (emp_id, proj_id, random.choice(roles), hours))
    conn.commit()

def main():
    print(f"Connecting to {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}...")
    conn = psycopg2.connect(**DB_CONFIG)

    print("Creating schema...")
    generate_schema(conn)

    print(f"Generating {NUM_RECORDS} employees across 20 departments...")
    dept_ids = generate_departments(conn)
    emp_ids = generate_employees(conn, dept_ids, count=NUM_RECORDS)
    generate_projects(conn, dept_ids, count=100)
    generate_assignments(conn, len(emp_ids), 100)

    # Verify
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM employees")
        emp_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM departments")
        dept_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM projects")
        proj_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM assignments")
        assign_count = cur.fetchone()[0]

    print(f"\nGenerated data summary:")
    print(f"  Departments:  {dept_count}")
    print(f"  Employees:    {emp_count}")
    print(f"  Projects:     {proj_count}")
    print(f"  Assignments:  {assign_count}")

    conn.close()
    print("Done!")

if __name__ == '__main__':
    main()
```

### Running the Pipeline

```bash
# Start everything
docker compose up -d

# Watch the generator logs
docker compose logs -f data-generator

# Access pgAdmin at http://localhost:5050
# Connect to test-db with user: testuser, password: testpass

# Or query directly
docker compose exec test-db psql -U testuser -d testdb -c "
SELECT d.name, COUNT(e.id) as emp_count, AVG(e.salary) as avg_salary
FROM departments d
LEFT JOIN employees e ON d.id = e.department_id
GROUP BY d.name
ORDER BY emp_count DESC
LIMIT 10;"
```

## Comparison: When to Use Each Tool

| Criteria | Faker | Greenmask | Custom Pipeline |
|---|---|---|---|
| **Data realism** | Good (statistical) | Perfect (real distributions) | Depends on implementation |
| **Setup complexity** | Low (pip install) | Medium (binary + config) | High (custom code) |
| **Database support** | Any (generates files) | PostgreSQL only | Any |
| **PII compliance** | Excellent (no real data) | Excellent (masks real data) | Depends on approach |
| **Referential integrity** | Manual | Automatic | Manual |
| **CI/CD friendly** | Yes | Yes (single binary) | Yes |
| **Best for** | Dev, unit tests, demos | Staging, QA, load testing | Complex domain models |

### Decision Guide

**Use Faker when:**
- You need quick test data for development or demos
- Your application doesn't depend on production data distributions
- You want fully reproducible datasets (seeded generation)
- You're testing with databases other than PostgreSQL

**Use Greenmask when:**
- You need production-like data with PII removed
- Your tests depend on real data distributions and edge cases
- You must maintain referential integrity across dozens of tables
- Compliance requires documented, auditable masking procedures

**Use a Custom Pipeline when:**
- Your domain has complex business rules that Faker can't model
- You need to generate data across multiple databases simultaneously
- You want to combine synthetic generation with selective masking
- You have specific performance or volume requirements

## Advanced: Combining Faker + Greenmask

The most powerful setup uses both tools together — Faker generates baseline synthetic data, then Greenmask applies additional masking layers for compliance:

```yaml
# Hybrid approach: Faker generates, Greenmask validates and masks edge cases
transformations:
  - schema: public
    name: employees
    transformers:
      # Faker already generated synthetic emails, but add domain normalization
      - name: Template
        params:
          column: email
          template: "{{ .email | split \"@\" | first }}@company-test.local"

      # Ensure all salaries fall within policy bounds
      - name: RandomFloat
        params:
          column: salary
          min: 35000.00
          max: 200000.00
          keep_null: false

      # Mask any accidentally-real names that slipped through
      - name: RandomString
        params:
          column: first_name
          min: 3
          max: 15
          type: name
```

## Conclusion

Self-hosted test data management is not just a technical choice — it's a compliance necessity and a productivity multiplier. In 2026, the combination of Faker for synthetic generation and Greenmask for PostgreSQL masking covers the vast majority of test data needs for engineering teams.

Start with Faker for quick wins: a few Python scripts can replace hours of manual data entry for development and testing. Add Greenmask when you need to safely use production data patterns in staging environments. And build a custom pipeline when your domain complexity demands something tailored.

All of these tools run entirely on your infrastructure, require no external API calls, and integrate cleanly into existing CI/CD pipelines. Your test data stays yours — from generation to cleanup.
