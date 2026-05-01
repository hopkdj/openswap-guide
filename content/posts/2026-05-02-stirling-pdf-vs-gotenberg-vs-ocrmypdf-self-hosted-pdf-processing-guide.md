---
title: "Stirling-PDF vs Gotenberg vs OCRmyPDF: Self-Hosted PDF Processing Guide 2026"
date: 2026-05-02
tags: ["pdf", "document", "self-hosted", "api", "docker", "comparison"]
draft: false
description: "Compare Stirling-PDF, Gotenberg, and OCRmyPDF for self-hosted PDF processing. Choose between a web-based toolkit, an API-first converter, and an OCR engine."
---

If you handle PDFs — whether that is merging documents, converting HTML to PDF, adding watermarks, or extracting text from scanned images — you have three main self-hosted options, each with a very different approach. Stirling-PDF gives you a full web interface with 50+ PDF tools. Gotenberg provides a Docker-based HTTP API for programmatic PDF generation and conversion. OCRmyPDF adds optical character recognition to scanned PDFs, making them searchable and accessible.

In this guide, we compare all three tools side by side so you can pick the right one for your workflow — or combine them for a complete self-hosted PDF processing pipeline.

## Quick Comparison

| Feature | Stirling-PDF | Gotenberg | OCRmyPDF |
|---------|-------------|-----------|----------|
| GitHub Stars | 78,057 | 11,926 | 33,508 |
| Language | Java (Spring Boot) | Go | Python |
| Interface | Web UI + REST API | REST API only | CLI only |
| Primary Use Case | PDF manipulation toolkit | HTML/Office to PDF conversion | OCR for scanned PDFs |
| Docker Image | `frooodle/s-pdf:latest` | `gotenberg/gotenberg:8` | `jbarlow83/ocrmypdf` |
| Merge/Split PDFs | Yes | No | No |
| Convert to PDF | Yes (limited) | Yes (HTML, Markdown, Office) | No |
| OCR Text Recognition | No | No | Yes |
| PDF Compression | Yes | No | Yes (during OCR) |
| Password Protection | Yes | No | No |
| Multi-language OCR | No | N/A | Yes (100+ languages) |
| Self-Hosted | Yes (Docker) | Yes (Docker) | Yes (Docker, local) |

## Stirling-PDF: The All-in-One PDF Toolkit

Stirling-PDF is a web-based PDF manipulation application with over 50 built-in tools. It is designed for users who need to perform PDF operations through a browser interface — merge, split, rotate, compress, convert, sign, watermark, and more — without uploading files to a third-party service.

### Docker Deployment

```yaml
services:
  stirling-pdf:
    image: frooodle/s-pdf:latest
    ports:
      - "8080:8080"
    volumes:
      - ./data:/usr/share/tessdata
      - ./configs:/configs
    environment:
      - DOCKER_ENABLE_SECURITY=false
      - INSTALL_BOOK_AND_ADVANCED_HTML_OPS=false
      - LANGS=en_US
    restart: unless-stopped
```

### Key Features

- **Merge and split** — combine multiple PDFs into one or extract specific pages
- **Convert formats** — PDF to images, images to PDF, PDF to Word/Excel (via LibreOffice)
- **Security** — add passwords, remove encryption, redact sensitive content
- **Editing** — add watermarks, rotate pages, reorder pages, flatten forms
- **OCR integration** — basic OCR via Tesseract (separate from OCRmyPDF's specialized engine)
- **Batch processing** — upload multiple files and process them in one operation
- **Multi-language UI** — translated into 30+ languages

### When to Use Stirling-PDF

Choose Stirling-PDF when you need a general-purpose PDF toolkit with a graphical interface. It is ideal for office workers, legal teams, and anyone who regularly manipulates PDFs but does not want to write code. The web UI makes it accessible to non-technical users.

## Gotenberg: API-First PDF Generation

Gotenberg is a Docker-based HTTP API that converts documents to PDF. Unlike Stirling-PDF's interactive toolkit approach, Gotenberg is designed for developers who need to generate PDFs programmatically from HTML, Markdown, Microsoft Office documents, or images.

### Docker Deployment

```yaml
services:
  gotenberg:
    image: gotenberg/gotenberg:8
    ports:
      - "3000:3000"
    command:
      - "gotenberg"
      - "--api-port=3000"
      - "--chromium-auto-start"
    restart: unless-stopped
```

### Convert HTML to PDF via API

```bash
curl --request POST \
  --url http://localhost:3000/forms/chromium/convert/html \
  --header "Content-Type: multipart/form-data" \
  --form "file=@invoice.html;type=text/html" \
  --form "waitDelay=500ms" \
  --form "nativePageRanges=1-3" \
  --output invoice.pdf
```

### Convert Markdown to PDF

```bash
curl --request POST \
  --url http://localhost:3000/forms/chromium/convert/markdown \
  --form "file=@report.md;type=text/markdown" \
  --form "header.html=@header.html" \
  --form "footer.html=@footer.html" \
  --form "paperSize=Letter" \
  --output report.pdf
```

### Convert Office Documents to PDF

```bash
curl --request POST \
  --url http://localhost:3000/forms/libreoffice/convert \
  --form "file=@presentation.pptx" \
  --form "landscape=true" \
  --form "exportFormFields=true" \
  --output presentation.pdf
```

### Key Features

- **HTML to PDF** — renders web pages with full CSS, JavaScript, and font support using headless Chromium
- **Markdown to PDF** — converts Markdown files with custom headers and footers
- **Office conversion** — converts DOCX, XLSX, PPTX, and other Office formats via LibreOffice
- **Merge PDFs** — combine multiple PDFs into a single document
- **PDF/A compliance** — generate archival-quality PDF/A-1b, PDF/A-2b, and PDF/A-3b documents
- **Custom headers/footers** — add page numbers, company logos, and legal disclaimers
- **Webhook support** — receive callbacks when conversion completes

### When to Use Gotenberg

Choose Gotenberg when you need to generate PDFs from a backend application. It is ideal for invoice generation, report creation, document conversion APIs, and any scenario where PDFs are produced programmatically rather than manually.

## OCRmyPDF: Searchable PDFs from Scanned Documents

OCRmyPDF adds an OCR text layer to scanned PDF files, making them searchable, selectable, and accessible. It uses Tesseract OCR under the hood and produces high-quality output with PDF/A compliance.

### Docker Deployment

```yaml
services:
  ocrmypdf:
    image: jbarlow83/ocrmypdf:latest
    volumes:
      - ./input:/input:ro
      - ./output:/output
    command: >
      ocrmypdf
      --language eng+fra
      --output-type pdfa
      --deskew
      --rotate-pages
      /input/scanned.pdf
      /output/searchable.pdf
    restart: "no"
```

### CLI Usage

```bash
# Basic OCR - add text layer to scanned PDF
ocrmypdf input_scanned.pdf output_searchable.pdf

# OCR with language detection and deskewing
ocrmypdf \
  --language eng+deu+fra \
  --deskew \
  --rotate-pages \
  --output-type pdfa \
  input_scanned.pdf output_searchable.pdf

# Process multiple files
for f in /scanned/*.pdf; do
  ocrmypdf --jobs 4 "$f" "/searchable/$(basename "$f")"
done
```

### Key Features

- **Tesseract OCR** — uses the industry-standard Tesseract engine with 100+ language packs
- **PDF/A output** — generates archival-quality PDF/A-2b documents suitable for long-term storage
- **Image preprocessing** — deskew, remove background noise, optimize resolution
- **Page rotation** — automatically detects and corrects page orientation
- **Parallel processing** — use multiple CPU cores for faster OCR on multi-page documents
- **Lossless optimization** — compress images without quality loss using JBIG2 and other techniques
- **Redo existing OCR** — replace a poor OCR layer with a new one

### When to Use OCRmyPDF

Choose OCRmyPDF when you need to digitize scanned documents. It is ideal for legal firms processing paper records, archives converting historical documents, and any organization that receives paper documents and needs to make them searchable.

## Why Self-Host PDF Processing?

Uploading sensitive documents to free online PDF tools carries real risks. Those services process your files on unknown servers, often with no encryption in transit and no guarantee of deletion afterward. Contracts, financial statements, medical records, and internal documents should never leave your infrastructure.

Self-hosting PDF tools gives you full control over document handling. Files never leave your server, you control access with your own authentication, and you can integrate processing into your existing pipelines. For teams handling regulated data, self-hosting is not optional — it is a compliance requirement.

For document signing workflows, see our [DocuSeal vs OpenSign vs LibreSign guide](../2026-04-24-docuseal-vs-opensign-vs-libresign-self-hosted-esignature-guide/) to handle legally binding signatures. For general file sharing and collaboration, our [file upload server comparison](../2026-04-25-zipline-vs-sharex-upload-server-vs-flowinity-self-hosted-file-upload-screenshot-server-guide-2026/) covers complementary tools.

## Combining All Three Tools

A complete self-hosted PDF pipeline might use all three tools together:

1. **OCRmyPDF** processes incoming scanned documents to make them searchable
2. **Gotenberg** generates new PDFs from HTML templates (invoices, reports)
3. **Stirling-PDF** provides a user-facing interface for manual operations (merge, split, rotate)

```yaml
services:
  stirling-pdf:
    image: frooodle/s-pdf:latest
    ports:
      - "8080:8080"

  gotenberg:
    image: gotenberg/gotenberg:8
    ports:
      - "3000:3000"

  ocrmypdf:
    image: jbarlow83/ocrmypdf:latest
    # Run on-demand, not as a long-lived service
```

## FAQ

### Can Stirling-PDF do OCR?

Stirling-PDF includes basic OCR via Tesseract, but it is not as capable as OCRmyPDF. Stirling-PDF's OCR is designed for simple text extraction, while OCRmyPDF offers advanced preprocessing (deskew, rotate, optimize), PDF/A compliance, and multi-language support. For serious OCR workloads, use OCRmyPDF alongside Stirling-PDF.

### Does Gotenberg support PDF editing like merging or splitting?

Gotenberg supports merging multiple PDFs into one via its `/forms/merge` endpoint, but it does not support page extraction, rotation, or other manipulation features. For those operations, use Stirling-PDF or a dedicated PDF library like `qpdf` or `pdftk`.

### How much disk space does OCRmyPDF need for large documents?

OCRmyPDF creates temporary files during processing. For a 100-page scanned PDF at 300 DPI, expect 500MB–1GB of temporary storage. The `--jobs` flag controls parallelism — more jobs means more temporary space but faster processing.

### Can Gotenberg handle custom fonts and CSS?

Yes. Gotenberg uses headless Chromium, which supports any font and CSS you include in your HTML. Upload custom fonts via the API or mount them in the Docker container. You can also use Google Fonts by including the appropriate `<link>` tags in your HTML.

### Are these tools suitable for production use?

All three are used in production by thousands of organizations. Stirling-PDF has 78K+ GitHub stars and active weekly releases. Gotenberg is used by major enterprises for document generation. OCRmyPDF is recommended by national archives and government agencies for document digitization projects.

### Do any of these tools require an internet connection?

No. Once the Docker images are pulled, all three tools operate entirely offline. OCRmyPDF downloads language packs during image build, but processing happens locally. Stirling-PDF and Gotenberg have no external dependencies at runtime.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Stirling-PDF vs Gotenberg vs OCRmyPDF: Self-Hosted PDF Processing Guide 2026",
  "description": "Compare Stirling-PDF, Gotenberg, and OCRmyPDF for self-hosted PDF processing. Choose between a web-based toolkit, an API-first converter, and an OCR engine.",
  "datePublished": "2026-05-02",
  "dateModified": "2026-05-02",
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
