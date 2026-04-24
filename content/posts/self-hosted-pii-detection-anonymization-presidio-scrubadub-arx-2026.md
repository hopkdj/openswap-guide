---
title: "Self-Hosted PII Detection & Anonymization: Presidio vs scrubadub vs ARX (2026)"
date: 2026-04-24
tags: ["comparison", "guide", "self-hosted", "privacy", "data-protection"]
draft: false
description: "Compare self-hosted PII detection and data anonymization tools — Microsoft Presidio, scrubadub, and ARX. Complete Docker deployment guides, API examples, and privacy model comparison for GDPR compliance."
---

Processing user data means handling sensitive information — names, emails, phone numbers, credit card numbers, social security numbers, and health records. Whether you are building a data pipeline, preparing datasets for testing, or enforcing GDPR compliance, you need reliable tools to detect and anonymize personally identifiable information (PII) before it leaves your infrastructure.

Cloud-based PII detection services require sending your data to third-party APIs. For organizations handling health records (PHI), financial data, or anything subject to GDPR, CCPA, or HIPAA, that is not acceptable. Self-hosted PII detection and anonymization tools keep everything on your own servers.

This guide compares three open-source solutions for PII detection and data anonymization: **Microsoft Presidio**, **scrubadub**, and **ARX Data Anonymization**. Each takes a fundamentally different approach — NLP-based detection, regex/pattern matching, and statistical anonymization respectively.

## Why Self-Host PII Detection?

Running PII detection on your own infrastructure offers several critical advantages over cloud services:

- **Data never leaves your network** — no third-party API calls with sensitive payloads
- **GDPR/HIPAA compliance** — you maintain full control over where data is processed
- **No per-call pricing** — cloud PII detection APIs charge per request; self-hosted tools are free at any scale
- **Customizable detection rules** — add organization-specific PII patterns (employee IDs, internal codes)
- **Deterministic anonymization** — consistent tokenization or hashing for referential integrity across datasets

## Comparison Overview

| Feature | Microsoft Presidio | scrubadub | ARX Data Anonymization |
|---|---|---|---|
| **GitHub Stars** | 7,750 | 422 | 710 |
| **Language** | Python | Python | Java |
| **Last Updated** | April 2026 | September 2023 | October 2025 |
| **License** | MIT | MIT | Apache 2.0 |
| **Detection Method** | NLP (spaCy) + regex + checksum | Regex + spaCy | Statistical models |
| **Anonymization Types** | Replace, redact, hash, mask, encrypt | Replace, remove | k-anonymity, l-diversity, t-closeness, differential privacy |
| **Docker Support** | Official images + compose | Library (pip install) | Desktop app + community images |
| **REST API** | Yes (built-in) | No (Python library) | No (Java GUI) |
| **Image PII Detection** | Yes (facial recognition) | No | No |
| **Batch Processing** | Yes | Yes | Yes |
| **Custom Recognizers** | Yes | Yes | Yes |

## Microsoft Presidio — NLP-Powered PII Detection

[Microsoft Presidio](https://github.com/microsoft/presidio) is the most popular open-source PII detection framework, with over 7,750 GitHub stars and active development. It uses Natural Language Processing (NLP) via spaCy combined with pattern matching (regex), checksum validation (Luhn algorithm for credit cards), and context analysis to identify sensitive data in text and images.

Presidio has two main components:
- **presidio-analyzer** — detects PII entities in text and images
- **presidio-anonymizer** — transforms detected entities using various operators (replace, mask, hash, encrypt, redact)

### What Presidio Can Detect

Presidio ships with 30+ built-in recognizers covering:

- **Personal identifiers**: Name, email, phone, SSN, passport, driver's license
- **Financial data**: Credit card numbers (with Luhn validation), IBAN, bank routing
- **Health records**: Medical license numbers, ICD codes (US/EU)
- **Digital identifiers**: IP addresses, URLs, cryptocurrency wallets
- **Location data**: US/UK addresses, geographic coordinates

The NLP model (based on spaCy's NER) catches PII that regex patterns miss — like person names and organizations in free-form text.

### Docker Deployment

Presidio provides official Docker images for all components. The simplest deployment uses Docker Compose to run the analyzer and anonymizer services:

```yaml
version: "3.8"
services:
  presidio-anonymizer:
    image: mcr.microsoft.com/presidio-anonymizer:latest
    ports:
      - "5001:5001"
    environment:
      - PORT=5001

  presidio-analyzer:
    image: mcr.microsoft.com/presidio-analyzer:latest
    ports:
      - "5002:5001"
    environment:
      - PORT=5001
      - ANALYZER_ENTITIES=PERSON,EMAIL,PHONE_NUMBER,CREDIT_CARD,US_SSN
    depends_on:
      - presidio-anonymizer
```

Start the services:

```bash
docker compose up -d
```

### Using the Presidio API

Once running, analyze text via the REST API:

```bash
curl -X POST http://localhost:5002/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "John Smith lives in Seattle. His SSN is 123-45-6789 and his email is john@example.com",
    "language": "en"
  }'
```

Response:

```json
[
  {
    "entity_type": "PERSON",
    "start": 0,
    "end": 10,
    "score": 0.85
  },
  {
    "entity_type": "US_SSN",
    "start": 38,
    "end": 49,
    "score": 0.95
  },
  {
    "entity_type": "EMAIL_ADDRESS",
    "start": 66,
    "end": 82,
    "score": 1.0
  }
]
```

Anonymize the detected entities:

```bash
curl -X POST http://localhost:5001/anonymize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "John Smith lives in Seattle. His SSN is 123-45-6789",
    "analyzer_results": [
      {"entity_type": "PERSON", "start": 0, "end": 10, "score": 0.85},
      {"entity_type": "US_SSN", "start": 38, "end": 49, "score": 0.95}
    ],
    "anonymizers": {
      "PERSON": {"type": "replace", "new_value": "<REDACTED>"},
      "US_SSN": {"type": "mask", "masking_char": "*", "chars_to_mask": 4}
    }
  }'
```

Response: `{"text": "<REDACTED> lives in Seattle. His SSN is *****-**-6789"}`

### Custom Recognizers

Add organization-specific PII patterns:

```python
from presidio_analyzer import Pattern, PatternRecognizer

# Detect internal employee IDs (format: EMP-XXXXX)
employee_id_pattern = Pattern(name="employee_id", regex=r"EMP-\d{5}", score=0.85)
employee_recognizer = PatternRecognizer(
    supported_entity="EMPLOYEE_ID",
    patterns=[employee_id_pattern]
)
```

### Advanced: Presidio with Transformers

For higher detection accuracy, Presidio supports transformer-based NLP models:

```yaml
version: "3.8"
services:
  presidio-analyzer:
    image: mcr.microsoft.com/presidio-analyzer:latest
    ports:
      - "5002:5001"
    environment:
      - PORT=5001
      - TRANSFORMERS_FULL_MODEL=dslim/bert-base-NER
      - ENABLE_TRANSFORMERS=true
```

This uses a fine-tuned BERT model for NER, which improves detection accuracy for edge cases but requires more RAM (~4GB minimum).

## scrubadub — Lightweight PII Removal for Python

[scrubadub](https://github.com/LeapBeyond/scrubadub) is a Python library designed for one job: find and remove personally identifiable information from text. It uses a collection of "detectors" (regex patterns and spaCy NER) to identify PII, then replaces detected entities with generic tokens.

Unlike Presidio, scrubadub is not a service — it is a Python library you import directly into your application.

### Installation

```bash
pip install scrubadub
pip install scrubadub[spacy]  # for NER-based detection
```

### Basic Usage

```python
import scrubadub

text = "Contact John at john@example.com or call 555-123-4567"
cleaned = scrubadub.clean(text)
print(cleaned)
# Output: "Contact {{NAME}} at {{EMAIL}} or call {{PHONE}}"
```

By default, scrubadub replaces detected PII with type-tagged tokens (`{{NAME}}`, `{{EMAIL}}`, etc.) rather than generic placeholders. This preserves the data structure while removing actual values — useful for log analysis and debugging.

### Detector Configuration

scrubadub ships with several detectors out of the box:

```python
import scrubadub

# List available detectors
for detector in scrubadub.list_detectors():
    print(detector)
# Output: email, name_en_us, phone_en_us, twitter, url, etc.

# Use specific detectors only
cleaned = scrubadub.clean(
    "Reach out at john@example.com",
    detector_list=['email', 'name_en_us']
)
```

### Custom Detectors

Create custom PII detectors for your domain:

```python
import scrubadub
from scrubadub.detectors import RegexDetector

class EmployeeIdDetector(RegexDetector):
    """Detect internal employee IDs like EMP-12345"""
    name = 'employee_id'
    regex = r'EMP-\d{5}'
    replacement = '{{EMPLOYEE_ID}}'

# Register and use
scrubadub.add_detector(EmployeeIdDetector)
result = scrubadub.clean("User EMP-45678 submitted a request")
# Output: "User {{EMPLOYEE_ID}} submitted a request"
```

### When to Use scrubadub

scrubadub is ideal when:
- You need a lightweight dependency in an existing Python application
- Simple regex-based PII detection is sufficient
- You do not want to run a separate service
- Your data is primarily in English with well-defined PII patterns

## ARX Data Anonymization — Statistical Privacy Models

[ARX](https://github.com/arx-deidentifier/arx) takes a fundamentally different approach from Presidio and scrubadub. Instead of finding and replacing individual PII fields, ARX applies **statistical anonymization models** to entire datasets to prevent re-identification.

ARX implements formal privacy models that are mathematically proven to limit re-identification risk:

- **k-anonymity** — every record is indistinguishable from at least k-1 other records
- **l-diversity** — sensitive attributes within each equivalence class have at least l distinct values
- **t-closeness** — the distribution of sensitive attributes in each group is close to the overall distribution
- **Differential privacy** — mathematically bounded privacy guarantee with configurable epsilon

### How ARX Works

ARX transforms quasi-identifiers (attributes that can be combined to re-identify individuals) through:

1. **Generalization** — replacing specific values with broader categories (e.g., age 34 → 30-39)
2. **Suppression** — removing records entirely when generalization is insufficient
3. **Microaggregation** — clustering similar records and replacing values with cluster centroids

### Docker Deployment (Community Image)

ARX does not provide official Docker images, but you can build one from the release JAR:

```yaml
version: "3.8"
services:
  arx-anonymizer:
    image: openjdk:17-jdk-slim
    volumes:
      - ./arx-data:/data
      - ./arx-output:/output
      - ./arx-config:/config
    command: >
      java -jar /opt/arx/arx.jar
        --config /config/anonymization.xml
        --input /data/dataset.csv
        --output /output/anonymized.csv
    working_dir: /opt/arx
```

Alternatively, download ARX directly:

```bash
# Download ARX
wget https://github.com/arx-deidentifier/arx/releases/download/3.9.1/arx-3.9.1.tar.gz
tar -xzf arx-3.9.1.tar.gz
cd arx-3.9.1

# Launch the GUI
./arx &

# Or run headless via command line
java -jar arx.jar --help
```

### Python Integration via pyarx

For automated pipelines, use the `pyarx` Python wrapper:

```python
import pandas as pd
from pyarx import ARXAnonymizer

# Load dataset
df = pd.read_csv("patient_data.csv")
# Columns: age, gender, zip_code, diagnosis, treatment

# Define quasi-identifiers and hierarchies
anonymizer = ARXAnonymizer()
anonymizer.add_quasi_identifier("age", "age_hierarchy.txt")
anonymizer.add_quasi_identifier("gender")
anonymizer.add_quasi_identifier("zip_code", "zip_hierarchy.txt")

# Define sensitive attribute
anonymizer.add_sensitive_attribute("diagnosis")

# Set privacy model: 3-anonymity
anonymizer.set_k_anonymity(3)

# Execute anonymization
result = anonymizer.anonymize(df)
print(f"Records suppressed: {result.suppressed}")
print(f"Information loss: {result.information_loss:.2%}")

result.anonymized_data.to_csv("anonymized_patients.csv", index=False)
```

### ARX GUI

ARX's standout feature is its interactive Java GUI, which provides:

- Visual hierarchy editors for generalization levels
- Real-time risk analysis (re-identification probability, distribution analysis)
- Privacy model comparison (see how k-anonymity vs l-diversity affects information loss)
- Export to multiple formats (CSV, XML, Microsoft Excel, ARFF)

This makes ARX particularly valuable for data stewards and privacy officers who need to **audit and verify** anonymization results before publishing datasets.

## Choosing the Right Tool

The three tools serve different use cases. Here is a decision framework:

### Use Presidio When

- You need a REST API service for real-time PII detection
- Your data contains free-form text (customer emails, support tickets, chat logs)
- You need to detect PII in images (scanned documents, ID cards)
- You want 30+ pre-built recognizers covering international PII types
- Active maintenance matters — Presidio is updated weekly

### Use scrubadub When

- You need a simple Python library, not a separate service
- Your data is structured or semi-structured (logs, database exports)
- You want tagged replacements (`{{EMAIL}}`, `{{PHONE}}`) for debugging
- Minimal dependencies are a priority
- English-language text is your primary use case

### Use ARX When

- You need formal privacy guarantees (k-anonymity, l-diversity, differential privacy)
- You are publishing research datasets or statistical reports
- You need to prevent re-identification through attribute linkage attacks
- You want visual risk analysis and interactive hierarchy configuration
- Your data is tabular (CSV, database tables) rather than free-form text

## Combined Pipeline: Best of All Three

In practice, many organizations combine these tools in a multi-stage pipeline:

```
Raw Data → scrubadub (quick filter) → Presidio (deep NER scan) → ARX (statistical anonymization) → Safe Output
```

Example pipeline using Python:

```python
import scrubadub
import requests
import json

def sanitize_pipeline(raw_text):
    # Stage 1: Quick regex-based scrub
    quick_clean = scrubadub.clean(raw_text)
    
    # Stage 2: Deep NER analysis via Presidio
    response = requests.post("http://localhost:5002/analyze", json={
        "text": quick_clean,
        "language": "en",
        "score_threshold": 0.75
    })
    findings = response.json()
    
    # Stage 3: Anonymize via Presidio
    anon_response = requests.post("http://localhost:5001/anonymize", json={
        "text": quick_clean,
        "analyzer_results": findings,
        "anonymizers": {
            "PERSON": {"type": "hash", "hash_type": "MD5"},
            "DEFAULT": {"type": "replace", "new_value": "[REDACTED]"}
        }
    })
    
    return anon_response.json()["text"]

# Process a customer support ticket
ticket = open("support_ticket_raw.txt").read()
safe_output = sanitize_pipeline(ticket)
print(safe_output)
```

For batch tabular data, add an ARX stage after text sanitization to apply k-anonymity on remaining quasi-identifiers before publishing the dataset.

For more on self-hosted privacy infrastructure, check out our [privacy stack guide](../privacy-stack-guide/) and [privacy-focused search engines comparison](../searxng-vs-whoogle-vs-librex-self-hosted-privacy-search-engines/). If you manage MFA and identity access, our [PrivacyIDEA vs LinOTP guide](../privacyidea-vs-linotp-self-hosted-mfa-server-guide-2026/) covers complementary authentication hardening.

## FAQ

### What is PII and why does it need anonymization?

Personally Identifiable Information (PII) is any data that can identify a specific individual — names, email addresses, phone numbers, social security numbers, medical records, and financial data. Regulations like GDPR, CCPA, and HIPAA require organizations to protect PII. Anonymization transforms PII so individuals cannot be identified, enabling safe data sharing, testing, and analytics.

### Is Microsoft Presidio free to use?

Yes. Microsoft Presidio is released under the MIT license, which allows free use in both personal and commercial projects. You can deploy it on your own servers without any licensing costs. The only infrastructure cost is the compute resources for running the Docker containers.

### Can Presidio detect PII in non-English text?

Presidio supports multiple languages out of the box, including English, Spanish, German, French, Italian, Portuguese, Dutch, and Hebrew. Each language has its own set of built-in recognizers tailored to that language's PII patterns (e.g., Spanish DNI numbers, German tax IDs). You can also add custom recognizers for any language.

### What is the difference between anonymization and pseudonymization?

Anonymization permanently removes or transforms PII so that re-identification is impossible. Pseudonymization replaces PII with artificial identifiers (tokens) that can be reversed with a lookup table. Anonymization is one-way; pseudonymization is reversible. GDPR treats anonymized data as no longer personal data, while pseudonymized data remains subject to GDPR.

### Which tool should I choose: Presidio, scrubadub, or ARX?

Choose **Presidio** if you need a REST API for real-time PII detection in free-form text or images. Choose **scrubadub** if you want a lightweight Python library for simple regex-based PII removal. Choose **ARX** if you need formal privacy guarantees (k-anonymity, differential privacy) for tabular dataset publication. Many organizations use all three in a combined pipeline.

### How does k-anonymity prevent re-identification?

k-anonymity ensures that every record in a dataset is indistinguishable from at least k-1 other records based on their quasi-identifiers (attributes like age, zip code, gender). For example, with k=5, an attacker knowing someone's age, zip code, and gender can narrow down to at least 5 records, making individual identification impossible from those attributes alone.

### Can I run Presidio without Docker?

Yes. Presidio can be installed directly via pip:

```bash
pip install presidio-analyzer
pip install presidio-anonymizer
```

You can then use it as a Python library without Docker. However, Docker is recommended for production deployments because it provides isolation, easy scaling, and consistent environments.

### Does ARX work with large datasets?

ARX supports datasets with millions of records, but performance depends on the complexity of your privacy model and the number of quasi-identifiers. For very large datasets (>10M rows), consider sampling or partitioning before anonymization. ARX provides an automated utility analysis to help determine the minimum k value that balances privacy with data utility.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PII Detection & Anonymization: Presidio vs scrubadub vs ARX (2026)",
  "description": "Compare self-hosted PII detection and data anonymization tools — Microsoft Presidio, scrubadub, and ARX. Complete Docker deployment guides, API examples, and privacy model comparison for GDPR compliance.",
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
