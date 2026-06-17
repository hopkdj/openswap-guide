---
title: "Self-Hosted CLI HTTP API Testing: Hurl vs HttpYac vs Restish Compared"
date: "2026-06-17"
tags: ["api-testing", "http", "cli-tools", "devops", "rest-api", "testing", "rust", "developer-tools"]
draft: false
---

## Introduction

API testing is a critical part of modern software development, but not every team needs a full Postman-like GUI or a heavy integration testing framework. Command-line HTTP testing tools offer a lightweight, scriptable, and CI/CD-friendly approach to validating API endpoints — all from your terminal.

In this guide, we compare three powerful CLI tools for HTTP API testing: **Hurl** (19,008 ★), **HttpYac** (840 ★), and **Restish** (1,314 ★). Each takes a different approach — declarative test files, VS Code-style `.http` file execution, or an interactive API exploration CLI.

| Feature | Hurl | HttpYac | Restish |
|---------|------|---------|---------|
| **Language** | Rust | TypeScript | Go |
| **Stars** | 19,008 ★ | 840 ★ | 1,314 ★ |
| **Approach** | Declarative .hurl files | .http/.rest files | Interactive CLI |
| **File Format** | `.hurl` (custom) | `.http`, `.rest` | N/A (CLI commands) |
| **Assertions** | Rich built-in | Basic + scripts | API discovery |
| **Variables** | Yes (captures) | Yes (environments) | N/A |
| **gRPC Support** | No | Yes | No |
| **WebSocket Support** | No | Yes | No |
| **GraphQL Support** | Yes | Yes | Limited |
| **CI/CD Integration** | Excellent (JUnit XML) | Good (exit codes) | Basic |
| **Install Method** | Single binary | npm | Single binary |
| **Learning Curve** | Medium | Low (if you know .http) | Low |
| **Multi-step Tests** | First-class | Supported | Not designed for |

## Hurl: Declarative HTTP Testing at Scale

Hurl (`Orange-OpenSource/hurl`) is a command-line tool that runs HTTP requests defined in a simple plain text format. Created by Orange (the French telecom), it's designed for running and testing HTTP requests with assertions, captures, and multi-step scenarios — think of it as "curl with superpowers."

### Installation

```bash
# Via Homebrew
brew install hurl

# Via Cargo
cargo install hurl

# Via npm
npm install -g @orangeopensource/hurl

# Download single binary from GitHub Releases
curl -L https://github.com/Orange-OpenSource/hurl/releases/latest/download/hurl-5.0.1-x86_64-unknown-linux-gnu.tar.gz | tar xz
sudo mv hurl-5.0.1/hurl /usr/local/bin/
```

### Writing Hurl Files

Hurl uses `.hurl` files with a simple, readable syntax:

```hurl
# test_api.hurl
GET https://api.example.com/users
HTTP 200
[Asserts]
jsonpath "$.data" exists
jsonpath "$.data[0].id" isInteger
jsonpath "$.data[0].email" matches "^[a-z]+@[a-z]+\.[a-z]+$"

POST https://api.example.com/auth/login
[Options]
variable: auth_token = undefined
[FormParams]
username: admin
password: secret123
HTTP 200
[Captures]
auth_token: jsonpath "$.token"

GET https://api.example.com/admin/dashboard
Authorization: Bearer {{auth_token}}
HTTP 200
```

### Running Tests

```bash
# Run a single test file
hurl --test test_api.hurl

# Run all .hurl files in a directory
hurl --test --glob "tests/**/*.hurl"

# Generate JUnit XML report for CI/CD
hurl --test --report-junit report.xml tests/*.hurl

# Run with variables from a file
hurl --variables-file env.prod.hurl tests/*.hurl
```

Hurl's standout feature is its assertion system — you can validate HTTP status codes, response headers, JSON body content, and even response timing. Combined with variable capture (extracting tokens from login responses to use in subsequent requests), it handles complex multi-step API workflows elegantly.

## HttpYac: VS Code REST Client for the Terminal

HttpYac (`AnWeber/httpyac`) brings the popular `.http` file format (used by the VS Code REST Client extension) to the command line. If your team already uses `.http` files for manual API testing, HttpYac lets you run those same files programmatically in CI/CD pipelines without any conversion.

### Installation

```bash
# Via npm
npm install -g httpyac

# Or run directly with npx
npx httpyac send tests/*.http
```

### Writing .http Files

HttpYac uses the standard `.http` file format familiar to VS Code REST Client users:

```http
### Login and get token
POST https://api.example.com/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "secret123"
}

### Use token for authenticated request
GET https://api.example.com/admin/users
Authorization: Bearer {{login.response.body.$.token}}
Content-Type: application/json
```

### Running Tests

```bash
# Run all .http files
httpyac send tests/*.http --all

# Run with environment variables
httpyac send tests/*.http -e production

# Output results as JSON
httpyac send tests/*.http --output response

# Filter specific requests by name
httpyac send tests/*.http --filter "Login"
```

HttpYac's key advantage is supporting gRPC, WebSocket, and MQTT in addition to HTTP/REST — making it a unified tool for testing all your API protocols. Its response chaining syntax (`{{login.response.body.$.token}}`) is intuitive for teams already familiar with the REST Client extension.

## Restish: Interactive API Exploration

Restish (`danielgtaylor/restish`) takes a different approach — it's an interactive CLI for exploring and interacting with REST-ish APIs. Rather than writing test files, you use Restish like a shell for APIs: navigate resources, discover endpoints, and inspect responses interactively.

### Installation

```bash
# Via Homebrew
brew install danielgtaylor/tap/restish

# Via Go
go install github.com/danielgtaylor/restish@latest

# Download binary from GitHub Releases
curl -L https://github.com/danielgtaylor/restish/releases/latest/download/restish-1.19.0-linux-amd64.tar.gz | tar xz
sudo mv restish /usr/local/bin/
```

### Setup and Usage

```bash
# Configure API base URLs
restish api configure https://api.example.com

# Interactive exploration
restish api                    # List available resources
restish api users              # List users
restish api users/42           # Get user 42
restish api users/42 posts     # Navigate relationships

# With authentication
restish api configure https://api.example.com --header "Authorization: Bearer token123"
```

Restish excels at API discovery and rapid prototyping. Its auto-pagination, response formatting (with syntax highlighting), and resource navigation make it the fastest way to explore an unfamiliar API from the terminal.

## Choosing Your HTTP Testing Tool

- **Choose Hurl** for comprehensive API testing in CI/CD — its assertion engine, variable capture, JUnit XML reporting, and integration-friendly design make it the best choice for automated testing pipelines. With 19,000+ stars and backing from Orange, it's the most battle-tested option.

- **Choose HttpYac** if your team already uses `.http` files in VS Code — you can reuse the same test files for both manual and automated testing, eliminating the need to maintain separate test suites. Its multi-protocol support (HTTP, gRPC, WebSocket, MQTT) is a bonus for teams working with diverse API types.

- **Choose Restish** for interactive API exploration and debugging — it's not a testing framework but rather a developer productivity tool for quickly interrogating APIs during development and debugging sessions. Think of it as `jq` for APIs.

For related API workflow tools, see our [webhook testing guide](../2026-04-24-webhook-site-vs-httpbin-vs-mockbin-self-hosted-webhook-testing-guide-2026/), our [gRPC client tools comparison](../2026-04-27-grpcurl-vs-grpcui-vs-evans-self-hosted-grpc-client-tools-guide-2026/), and our [API documentation tools guide](../2026-05-01-self-hosted-api-documentation-scalar-redoc-rapiddoc-openapi-guide/).

## Building an API Testing Pipeline

Integrating CLI HTTP testing into your CI/CD pipeline transforms API validation from a manual chore into an automated gate. Here's a practical workflow:

First, write Hurl test files that cover your critical API paths — authentication, CRUD operations, and edge cases. Store them alongside your application code in a `tests/api/` directory. Then, add a CI step that runs Hurl against a staging or ephemeral environment after deployment:

```bash
# In your CI pipeline (GitHub Actions example)
- name: API Tests
  run: |
    hurl --test --report-junit api-report.xml tests/api/*.hurl       --variable host=${{ env.STAGING_URL }}
- name: Publish Results
  uses: dorny/test-reporter@v1
  with:
    name: API Tests
    path: api-report.xml
    reporter: java-junit
```

This pattern ensures that every deployment is validated against your API contract before reaching production. Combined with OpenAPI schema validation and contract testing, CLI HTTP testing tools provide a lightweight but powerful layer in your quality assurance pipeline.

## FAQ

### How is Hurl different from curl?

Hurl builds on curl's HTTP engine but adds a testing framework with assertions, variable capture, multi-step scenarios, and structured reporting. While curl is a general-purpose HTTP client, Hurl is purpose-built for testing. Hurl files are also more readable than shell scripts wrapping curl commands, making them easier to maintain and review.

### Can I use HttpYac files from VS Code REST Client?

Yes — HttpYac supports the same `.http` file format as the VS Code REST Client extension. However, be aware that HttpYac has its own variable syntax (`{{response.body.$.field}}`) and some VS Code-specific features may not translate perfectly. Test your files in CI before relying on complete compatibility.

### Is Restish suitable for automated testing?

Restish is primarily designed for interactive API exploration, not automated testing. It doesn't have built-in assertions, JUnit reporting, or multi-step test scenarios. For CI/CD testing, use Hurl or HttpYac instead. Restish shines during development and debugging when you need to quickly explore API responses.

### How do I handle authentication in these tools?

Hurl supports Basic Auth, Bearer tokens, and variable capture from login responses. HttpYac supports environment variables and response chaining for tokens. Restish supports header-based authentication configured via CLI. All three can work with OAuth2 flows, though you'll typically need to handle token refresh externally or via scripts.

### Which tool integrates best with CI/CD pipelines?

Hurl has the best CI/CD integration with native JUnit XML output, `--test` mode (non-zero exit on failure), glob pattern support for test discovery, and variables files for environment-specific configuration. It's the clear winner for automated testing pipelines.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted CLI HTTP API Testing: Hurl vs HttpYac vs Restish Compared",
  "description": "Compare Hurl (19,008★), HttpYac (840★), and Restish (1,314★) for command-line HTTP API testing. Includes .hurl file examples, CI/CD integration, and choosing the right tool for your API testing workflow.",
  "datePublished": "2026-06-17",
  "dateModified": "2026-06-17",
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
