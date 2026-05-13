---
title: "Self-Hosted Email Template Rendering — MJML Server vs MJML-API vs Handlebars-Mail"
date: "2026-05-14"
tags: ["email", "templates", "mjml", "api-server", "development-tools"]
draft: false
---

Creating responsive, well-formatted emails that look good across all email clients is notoriously difficult. HTML email rendering varies wildly between Gmail, Outlook, Apple Mail, and dozens of other clients. **MJML** (Markup JavaMail Language) solves this by providing a simplified markup language that compiles to responsive, cross-client-compatible HTML.

While MJML is typically used as a CLI tool or npm package, self-hosting an MJML rendering server provides API-based template rendering for microservices, CI/CD pipelines, and multi-tenant applications. In this guide, we compare three open-source approaches to self-hosted email template rendering: **MJML Server (Express)**, **MJML-API (Symfony)**, and **Handlebars-Mail templating**.

## Why Self-Host Email Template Rendering?

Third-party email template services like SendGrid's Template Engine, Mailgun's Templates, or Postmark's Template API offer convenient rendering — but they lock you into specific email delivery providers, add latency to your email pipeline, and limit template customization. Self-hosting gives you:

- **Provider independence** — render templates locally, send through any SMTP server
- **Lower latency** — no network round-trip to external rendering APIs
- **Custom template logic** — integrate with your own data sources and templating engines
- **Data privacy** — template content and recipient data never leave your infrastructure
- **Cost savings** — no per-email or per-template rendering charges

For organizations sending transactional emails, newsletters, or notifications at scale, a self-hosted rendering layer is a valuable infrastructure component.

## Tool Comparison

| Feature | MJML Server (Express) | MJML-API (Symfony) | Handlebars-Mail |
|---------|----------------------|---------------------|-----------------|
| GitHub Stars | 47+ | 20+ | Community pattern |
| Language | Node.js/Express | PHP/Symfony | Node.js/Handlebars |
| MJML Support | Native | Via mjml-php | Via mjml npm |
| REST API | Yes | Yes | Custom |
| Template Storage | Filesystem | Database | Filesystem |
| Multi-tenant | Manual | Built-in | Manual |
| Docker Support | Yes | Yes | Yes |
| Active Development | Stable | Stable | Community |
| License | MIT | MIT | MIT |

## 1. MJML Server (Express) — danihodovic/mjml-server

**MJML Server** is a lightweight Express.js wrapper around the MJML compiler that exposes an HTTP API for rendering email templates. Send MJML or JSON with template variables, receive compiled HTML email ready for sending.

### Key Features

- **Simple REST API** — POST MJML markup or JSON, get rendered HTML
- **Variable injection** — support for Handlebars-style template variables
- **Minimal dependencies** — thin wrapper around the official MJML compiler
- **Docker ready** — easy containerization
- **Stateless** — no database required, perfect for horizontal scaling

### Docker Compose Configuration

```yaml
version: '3.8'
services:
  mjml-server:
    image: node:18-alpine
    container_name: mjml-server
    working_dir: /app
    command: sh -c "npm install mjml-server && npx mjml-server"
    ports:
      - "3000:3000"
    volumes:
      - ./templates:/app/templates
    restart: unless-stopped
```

### API Usage

```bash
# Render MJML markup directly
curl -X POST http://localhost:3000/render   -H "Content-Type: application/json"   -d '{
    "mjml": "<mjml><mj-body><mj-section><mj-column><mj-text>Hello World</mj-text></mj-column></mj-section></mj-body></mjml>"
  }'

# Render with template variables
curl -X POST http://localhost:3000/render   -H "Content-Type: application/json"   -d '{
    "template": "welcome.mjml",
    "data": {
      "name": "John",
      "activation_link": "https://example.com/activate/abc123"
    }
  }'
```

### Template File Structure

```
templates/
├── welcome.mjml
├── password-reset.mjml
├── order-confirmation.mjml
└── newsletter.mjml
```

### When to Use

MJML Server (Express) is ideal for Node.js-based applications that need a simple, stateless email rendering microservice. Its minimal design makes it easy to deploy alongside existing services.

## 2. MJML-API (Symfony) — shyim/mjml-server

**MJML-API** is a PHP/Symfony-based REST API server for MJML rendering. It provides a more structured approach with database-backed template storage, validation, and multi-tenant support — making it suitable for SaaS platforms and agencies managing email templates for multiple clients.

### Key Features

- **Database-backed templates** — store and version templates in a database
- **Template validation** — validate MJML syntax before saving
- **Multi-tenant support** — organize templates by organization/client
- **RESTful API** — full CRUD operations for templates
- **Symfony ecosystem** — integrates with existing Symfony applications

### Docker Compose Configuration

```yaml
version: '3.8'
services:
  mjml-api:
    image: php:8.2-fpm
    container_name: mjml-api
    working_dir: /app
    command: php -S 0.0.0.0:8080 -t public/
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=mysql://mjml:mjml-pass@db:3306/mjml_templates
    volumes:
      - ./src:/app
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: mariadb:10.11
    container_name: mjml-api-db
    environment:
      - MYSQL_ROOT_PASSWORD=root-pass
      - MYSQL_DATABASE=mjml_templates
      - MYSQL_USER=mjml
      - MYSQL_PASSWORD=mjml-pass
    volumes:
      - mjml-db:/var/lib/mysql
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - mjml-api

volumes:
  mjml-db:
```

### API Endpoints

```bash
# Create a new template
curl -X POST http://localhost:8080/api/templates   -H "Content-Type: application/json"   -d '{
    "name": "welcome-email",
    "subject": "Welcome to {{company_name}}",
    "content": "<mjml><mj-body>...</mj-body></mjml>",
    "variables": ["company_name", "user_name"]
  }'

# Render a stored template
curl -X POST http://localhost:8080/api/templates/welcome-email/render   -H "Content-Type: application/json"   -d '{
    "company_name": "Acme Corp",
    "user_name": "Jane Doe"
  }'

# List all templates
curl http://localhost:8080/api/templates
```

### When to Use

MJML-API is best for PHP/Symfony applications or organizations that need structured template management with versioning, validation, and multi-tenant support.

## 3. Handlebars-Mail with MJML Compilation

**Handlebars-Mail** represents a pattern (rather than a single tool) where you combine Handlebars templating with MJML compilation in a Node.js service. This approach gives you the full power of Handlebars helpers, partials, and layouts alongside MJML's responsive email rendering.

### Key Features

- **Handlebars templating** — full helper system, partials, and layout support
- **MJML compilation** — produces responsive HTML from MJML markup
- **Custom helpers** — build domain-specific template helpers
- **Pre-compiled templates** — cache compiled templates for performance
- **Flexible architecture** — adapt to any application's needs

### Implementation

```javascript
// email-renderer.js
const mjml2html = require('mjml');
const Handlebars = require('handlebars');
const fs = require('fs').promises;

class EmailRenderer {
  constructor(templateDir) {
    this.templateDir = templateDir;
    this.cache = new Map();
    this.registerHelpers();
  }

  registerHelpers() {
    Handlebars.registerHelper('formatCurrency', (amount) => {
      return new Handlebars.SafeString(
        `$${Number(amount).toFixed(2)}`
      );
    });

    Handlebars.registerHelper('dateFormat', (date, format) => {
      return new Date(date).toLocaleDateString('en-US');
    });
  }

  async render(templateName, data) {
    // Check cache first
    if (!this.cache.has(templateName)) {
      const mjml = await fs.readFile(
        `${this.templateDir}/${templateName}.mjml`,
        'utf8'
      );
      const compiled = Handlebars.compile(mjml);
      this.cache.set(templateName, compiled);
    }

    const template = this.cache.get(templateName);
    const mjmlContent = template(data);

    // Compile MJML to HTML
    const { html, errors } = mjml2html(mjmlContent, {
      validationLevel: 'strict',
      minify: true
    });

    if (errors.length > 0) {
      console.error('MJML errors:', errors);
      throw new Error('MJML compilation failed');
    }

    return html;
  }
}

module.exports = EmailRenderer;
```

### Docker Compose Configuration

```yaml
version: '3.8'
services:
  email-renderer:
    build: .
    container_name: email-renderer
    ports:
      - "3001:3000"
    volumes:
      - ./templates:/app/templates
    environment:
      - NODE_ENV=production
      - TEMPLATE_CACHE_TTL=3600
    restart: unless-stopped
```

### Dockerfile

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
```

### When to Use

The Handlebars-MJML pattern is ideal for teams that need complex template logic (conditionals, loops, custom formatters) alongside responsive email rendering. It's the most flexible approach but requires more development effort than pre-built solutions.

## Email Template Architecture

```
Application → Template Renderer → MJML Compiler → Responsive HTML → SMTP Server
     ↓              ↓                  ↓                ↓              ↓
  Trigger      Load Template      Validate MJML    Cross-client    Deliver to
  Event        + Inject Data      + Minify         Compatible      Recipient
```

### Template Versioning Strategy

```bash
# Store templates in version control
git add templates/*.mjml
git commit -m "feat: add welcome email template v2"

# Tag releases for rollback capability
git tag email-templates-v2026.05
git push origin --tags
```

### Testing Rendered Templates

```bash
# Render and save to file for preview
curl -X POST http://localhost:3000/render   -H "Content-Type: application/json"   -d '{"template": "welcome", "data": {"name": "Test User"}}'   -o /tmp/test-email.html

# Open in browser for visual testing
xdg-open /tmp/test-email.html

# Test across email clients using Litmus or Email on Acid
# Or use the open-source email-client-tester
```

For related reading, see our [SMTP relay comparison](../2026-04-26-postal-vs-stalwart-vs-haraka-self-hosted-smtp-relay-guide-2/) for self-hosted email delivery platforms, our [email sieve filtering guide](../2026-05-12-self-hosted-email-sieve-filtering-pigeonhole-rspamd-cyrus-g/) for server-side email processing, and our [email authentication deep dive](../self-hosted-dmarc-analysis-email-authentication-parsedmarc-opendmarc-g/) for ensuring deliverability.

## FAQ

### What is MJML and why should I use it?

MJML is a markup language designed specifically for creating responsive emails. Instead of writing complex nested tables and inline CSS that work across email clients, you write simple MJML tags that compile to compatible HTML. This saves hours of debugging email rendering issues.

### Why self-host an MJML rendering server instead of using the CLI?

A rendering server provides a stateless API that any service in your architecture can call — frontend apps, backend services, CI/CD pipelines, or cron jobs. It centralizes template management, enables caching, and removes the need to install Node.js and MJML on every server that sends emails.

### Can I use these tools with existing email templates?

Yes. All three approaches can import existing HTML email templates, though converting them to MJML markup will give you the best cross-client compatibility. MJML provides a [HTML-to-MJML converter](https://mjml.io/try-it-live) for this purpose.

### How do I preview rendered emails before sending?

Most email clients support previewing HTML files directly. Save the rendered output to an `.html` file and open it in your browser. For accurate cross-client testing, use services like Litmus, Email on Acid, or the open-source email-client-tester project.

### Can I use these tools for newsletters as well as transactional emails?

Yes. MJML supports all email types — transactional (password resets, order confirmations), marketing (newsletters, promotions), and notification emails. The template patterns are the same regardless of email type.

### How do I handle template localization (i18n)?

Store language-specific templates in separate directories (e.g., `templates/en/welcome.mjml`, `templates/de/welcome.mjml`) or use Handlebars helpers to inject translated strings based on the recipient's locale. The rendering server approach makes this easy by adding a `locale` parameter to the render request.

## Choosing the Right Email Template Rendering Solution

- **For simplicity**: MJML Server (Express) provides the quickest path from zero to a working rendering API with minimal setup.
- **For template management**: MJML-API (Symfony) offers database-backed storage, validation, and multi-tenant features for organized template workflows.
- **For maximum flexibility**: The Handlebars-MJML pattern gives you full control over template logic, custom helpers, and compilation pipelines.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Email Template Rendering — MJML Server vs MJML-API vs Handlebars-Mail",
  "description": "Compare self-hosted email template rendering solutions — MJML Server (Express), MJML-API (Symfony), and Handlebars-MJML compilation for responsive cross-client email generation.",
  "datePublished": "2026-05-14",
  "dateModified": "2026-05-14",
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
