---
title: "QuickChart vs bwip-js vs PHP-QRCode: Self-Hosted QR & Barcode API Servers 2026"
date: 2026-04-26
tags: ["comparison", "guide", "self-hosted", "api", "qr-code"]
draft: false
description: "Compare three open-source self-hosted QR code and barcode generation API servers — QuickChart, bwip-js, and chillerlan/php-qrcode — with Docker deployment guides and feature comparisons."
---

## Why Self-Host a QR Code & Barcode API

Every modern application needs to generate QR codes and barcodes — for two-factor authentication setup, product labeling, payment links, ticketing systems, and inventory management. Relying on third-party SaaS APIs means sending potentially sensitive data to external servers, accepting rate limits, and risking service outages beyond your control.

A self-hosted QR and barcode generation API gives you:

- **Full data privacy** — no data ever leaves your infrastructure
- **Zero rate limits** — generate millions of codes without hitting API quotas
- **Offline availability** — works even without internet access (warehouses, labs, air-gapped networks)
- **Cost savings** — no per-request pricing, unlimited volume at the cost of your own server resources
- **Customization** — full control over styling, output formats, and integration patterns

In this guide, we compare three production-ready open-source tools that can serve as self-hosted QR code and barcode generation backends: **QuickChart**, **bwip-js**, and **chillerlan/php-qrcode**.

| Feature | QuickChart | bwip-js | chillerlan/php-qrcode |
|---------|-----------|---------|----------------------|
| **Language** | JavaScript (Node.js) | JavaScript | PHP |
| **GitHub Stars** | 2,033 | 2,331 | 2,357 |
| **Last Updated** | 2024-09-21 | 2026-04-22 | 2026-03-30 |
| **QR Codes** | Yes | Yes | Yes |
| **Barcode Types** | 100+ (via bwip-js engine) | 100+ | QR only |
| **HTTP API** | Built-in REST API | Built-in HTTP server | Library + custom endpoint |
| **Docker Image** | Official (`ghcr.io/typpo/quickchart`) | Docker Compose deployable | Docker Compose deployable |
| **Output Formats** | PNG, SVG | PNG, SVG, Canvas | PNG, SVG, EPS, String |
| **Chart Generation** | Yes (Chart.js) | No | No |
| **Batch Generation** | No (single-image API) | No (single-image API) | Yes (programmatic loops) |
| **License** | MIT | MIT | MIT |
| **Self-Hosted Difficulty** | Easy (single container) | Easy (single container) | Moderate (PHP stack) |

## QuickChart — Full-Featured Chart & QR API Server

[QuickChart](https://quickchart.io/) is a self-hostable web API that generates both chart images (powered by Chart.js) and QR codes. While it is known primarily as a chart API, its QR code endpoint is fully featured and production-ready.

### Key Features

- Simple REST API — just hit a URL with query parameters
- Supports QR codes, barcodes, charts, and other visualizations
- Caching built in for repeated requests
- Docker image available at `ghcr.io/typpo/quickchart`

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  quickchart:
    image: ghcr.io/typpo/quickchart:latest
    container_name: quickchart
    restart: unless-stopped
    ports:
      - "3400:3400"
    environment:
      - PORT=3400
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3400/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

Start the service:

```bash
docker compose up -d
```

### Generating QR Codes

Once deployed, generate a QR code with a simple GET request:

```bash
curl -o qrcode.png "http://localhost:3400/qr?text=https://example.com&size=300&ecLevel=H"
```

Generate a barcode:

```bash
curl -o barcode.png "http://localhost:3400/barcode?bcid=code128&text=123456789012&scale=3"
```

### Use Cases

QuickChart excels when you need **both** QR codes and chart images from a single service. It is ideal for dashboards, reporting systems, and applications that need dynamic image generation.

## bwip-js — Barcode Writer in Pure JavaScript

[bwip-js](https://github.com/metafloor/bwip-js) is a barcode generation library that supports over 100 barcode symbologies, including QR Code, Data Matrix, PDF417, Code 128, EAN-13, UPC-A, and many more. It ships with a built-in HTTP server, making it a drop-in barcode API service.

### Key Features

- **100+ barcode types** — the most comprehensive barcode support of any tool in this comparison
- Pure JavaScript — runs anywhere Node.js runs
- Built-in HTTP server (`bwip-js-http`)
- Outputs PNG, SVG, and Canvas
- Actively maintained (last update: April 2026)

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  bwipjs:
    image: node:20-alpine
    container_name: bwipjs
    restart: unless-stopped
    working_dir: /app
    command: >
      sh -c "npm install -g bwip-js@latest && bwip-js-http --port 3030"
    ports:
      - "3030:3030"
    healthcheck:
      test: ["CMD", "wget", "--spider", "http://localhost:3030/bwip-js/?bcid=qrcode&text=healthcheck"]
      interval: 30s
      timeout: 5s
      retries: 3
```

Start the service:

```bash
docker compose up -d
```

### Generating Barcodes and QR Codes

The bwip-js HTTP server accepts GET requests with barcode parameters:

```bash
# Generate a QR code
curl -o qrcode.png "http://localhost:3030/bwip-js/?bcid=qrcode&text=Hello%20World&scale=3&eclevel=H"

# Generate a Code 128 barcode
curl -o barcode.png "http://localhost:3030/bwip-js/?bcid=code128&text=ITEM-2026-0042&scale=2&includetext"

# Generate an EAN-13 barcode for product labeling
curl -o ean13.png "http://localhost:3030/bwip-js/?bcid=ean13&text=5901234123457&scale=3&includetext"

# Generate a Data Matrix code for small-item marking
curl -o datamatrix.png "http://localhost:3030/bwip-js/?bcid=datamatrix&text=SerialNumber12345&scale=3"
```

### Supported Barcode Types

bwip-js supports a wide range of symbologies, making it the most versatile choice for industrial and commercial use:

- **2D codes**: QR Code, Data Matrix, PDF417, Aztec Code, MaxiCode
- **Retail**: EAN-13, EAN-8, UPC-A, UPC-E, ISBN
- **Logistics**: Code 128, Code 39, ITF-14, GS1-128
- **Healthcare**: HIBC, ISBT 128, Pharmacode
- **Postal**: PostNet, Planet, Royal Mail 4SC, Australian Post

### Use Cases

bwip-js is the best choice when you need **comprehensive barcode support** — retail product labeling, warehouse inventory systems, shipping labels, healthcare tracking, and any scenario requiring multiple barcode symbologies from a single service.

## chillerlan/php-qrcode — PHP QR Code Library

[chillerlan/php-qrcode](https://github.com/chillerlan/php-qrcode) is a modern PHP library for generating QR codes with advanced customization options. While it does not ship with a built-in HTTP server, it is trivially deployed as a PHP web service and offers the most flexible QR code styling of any tool in this comparison.

### Key Features

- **Advanced QR customization** — colors, gradients, module shapes, logos embedded in QR codes
- Multiple output formats: PNG, SVG, EPS, text (string), HTML
- QR code reading/decoding support
- Composer-installable for PHP projects
- Well-documented API with examples
- PHP 8.1+ compatible

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  php-qrcode:
    image: php:8.2-apache
    container_name: php-qrcode
    restart: unless-stopped
    ports:
      - "8080:80"
    volumes:
      - ./qr-server:/var/www/html
      - ./composer.json:/var/www/html/composer.json
    working_dir: /var/www/html
    command: >
      sh -c "apt-get update && apt-get install -y libpng-dev zip unzip &&
             docker-php-ext-install gd &&
             curl -sS https://getcomposer.org/installer | php &&
             php composer.phar install &&
             apache2-foreground"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/"]
      interval: 30s
      timeout: 5s
      retries: 3
```

### PHP API Endpoint

Create a simple `qr-server/api.php` file:

```php
<?php
require_once 'vendor/autoload.php';

use chillerlan\QRCode\QRCode;
use chillerlan\QRCode\Common\EccLevel;
use chillerlan\QRCode\Common\Version;
use chillerlan\QRCode\Output\QRImage;
use chillerlan\QRCode\Output\QRMarkupSVG;

$text = $_GET['text'] ?? 'https://example.com';
$format = $_GET['format'] ?? 'png';
$size = (int)($_GET['size'] ?? 300);
$ecLevel = $_GET['eclevel'] ?? 'M';

$options = [
    'outputType' => $format === 'svg' ? QRMarkupSVG::class : QRImage::class,
    'eccLevel' => constant("chillerlan\\QRCode\\Common\\EccLevel::$ecLevel"),
    'scale' => max(1, $size / 300),
];

$qrcode = new QRCode($options);
$qrOutput = $qrcode->render($text);

if ($format === 'svg') {
    header('Content-Type: image/svg+xml');
} else {
    header('Content-Type: image/png');
}

echo $qrOutput;
```

### Generating QR Codes

```bash
# Generate a standard QR code
curl -o qrcode.png "http://localhost:8080/api.php?text=https://example.com&format=png&size=300"

# Generate an SVG QR code with high error correction
curl -o qrcode.svg "http://localhost:8080/api.php?text=https://example.com&format=svg&eclevel=H"
```

### Use Cases

php-qrcode is ideal when you need **customized QR codes** — branded QR codes with company colors, QR codes with embedded logos, or QR codes with non-standard module shapes. It is also the best choice for PHP-based applications that want a native library rather than a separate microservice.

## Comparison: Which Tool Should You Choose?

| Criteria | QuickChart | bwip-js | php-qrcode |
|----------|-----------|---------|------------|
| **Easiest deployment** | Yes (single official image) | Moderate (Node base image) | Complex (PHP + Apache + GD) |
| **Most barcode types** | 100+ (via bwip-js engine) | 100+ (native) | QR only |
| **Best for QR styling** | Basic | Basic | Advanced (colors, logos, shapes) |
| **REST API out of the box** | Yes | Yes | Build your own |
| **Best ecosystem fit** | Node.js apps | Any app (HTTP API) | PHP apps |
| **Actively maintained** | Last update 2024-09 | Last update 2026-04 | Last update 2026-03 |
| **Best for** | Charts + QR in one service | All barcode types needed | Custom QR code branding |

### Decision Guide

- **Choose QuickChart** if you already need chart generation (Chart.js images) and want QR codes as a bonus from the same service. It is the easiest to deploy with an official Docker image.
- **Choose bwip-js** if you need to generate many different barcode types — Code 128, EAN-13, Data Matrix, PDF417, and more. It is the most versatile barcode engine.
- **Choose php-qrcode** if you need highly customized QR codes with branding (custom colors, embedded logos, unique module shapes) and your application is PHP-based.

## Reverse Proxy Configuration

For production deployment, place your QR/barcode API behind a reverse proxy. Here is an example Nginx configuration:

```nginx
server {
    listen 443 ssl http2;
    server_name qr.example.com;

    ssl_certificate     /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    location /qr {
        proxy_pass http://127.0.0.1:3400/qr;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /barcode {
        proxy_pass http://127.0.0.1:3030/bwip-js/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

For related reading on reverse proxy configurations, see our [complete mTLS guide](../self-hosted-mutual-tls-mtls-nginx-caddy-traefik-e/) and [API gateway comparison](../self-hosted-api-lifecycle-management-kong-apisix-tyk-gravitee-krakend-guide-2026/).

## FAQ

### What is the difference between QR codes and barcodes?

QR codes (Quick Response codes) are two-dimensional barcodes that can store more data in both horizontal and vertical dimensions. They can encode URLs, text, contact information, and up to several kilobytes of data. Traditional barcodes (like Code 128 or EAN-13) are one-dimensional and typically encode only numeric or alphanumeric identifiers. For product labeling, you may need both — barcodes for retail compatibility and QR codes for linking to digital content.

### Can I generate QR codes with embedded logos?

Yes, but support varies by tool. **chillerlan/php-qrcode** natively supports embedding images (logos) within QR codes through its output modules. QuickChart and bwip-js generate standard QR codes without logo overlay support — you would need to composite the logo afterward using an image processing library like ImageMagick or the `sharp` npm package.

### Which tool has the smallest Docker image footprint?

QuickChart uses a Node.js-based image typically around 200-300 MB. bwip-js running on `node:20-alpine` is approximately 150-200 MB. The php-qrcode setup with `php:8.2-apache` and GD extension is the largest at 400+ MB. If image size matters, bwip-js on Alpine is the most lightweight option.

### Can these tools generate barcodes for retail products?

Yes. **bwip-js** is the best choice for retail barcode generation, supporting EAN-13, EAN-8, UPC-A, UPC-E, ISBN, and GS1-128 — all common retail symbologies. QuickChart also supports these via its bwip-js backend engine. php-qrcode generates only QR codes, not traditional retail barcodes.

### How do I handle high-volume QR code generation?

All three tools are stateless and can be horizontally scaled. For QuickChart and bwip-js, place multiple instances behind a load balancer (HAProxy, Nginx, or Traefik) and distribute requests. For php-qrcode, scale the PHP-FPM pool or add more PHP containers behind a reverse proxy. Since QR code generation is CPU-light, a single container can typically handle hundreds of requests per second.

### Is it safe to use self-hosted QR codes for sensitive data?

Self-hosting ensures that the data you encode into QR codes never passes through a third-party service — this is critical for internal applications, healthcare, and finance. However, the QR code itself contains whatever data you encode. If you encode a URL to sensitive content, the QR code acts as a pointer and should be protected with authentication on the destination. For storing sensitive data directly in QR codes, use encryption before encoding.

## Self-Hosted QR & Barcode Tools Summary

| Tool | Best For | Deployment Complexity | Barcode Support |
|------|----------|----------------------|-----------------|
| QuickChart | Chart + QR combined API | Low (official Docker image) | 100+ types |
| bwip-js | Maximum barcode variety | Low-Medium (Node.js container) | 100+ types |
| php-qrcode | Custom QR code styling | Medium (PHP + Apache + GD) | QR only |

For more self-hosted API tools, check out our [screenshot and PDF generation API guide](../self-hosted-screenshot-pdf-generation-apis-gotenberg-playwright-puppeteer-guide-2026/) and [text-to-diagram platforms comparison](../self-hosted-text-to-diagram-platforms-kroki-plantuml-mermaid-guide-2026/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "QuickChart vs bwip-js vs PHP-QRCode: Self-Hosted QR & Barcode API Servers 2026",
  "description": "Compare three open-source self-hosted QR code and barcode generation API servers — QuickChart, bwip-js, and chillerlan/php-qrcode — with Docker deployment guides and feature comparisons.",
  "datePublished": "2026-04-26",
  "dateModified": "2026-04-26",
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
