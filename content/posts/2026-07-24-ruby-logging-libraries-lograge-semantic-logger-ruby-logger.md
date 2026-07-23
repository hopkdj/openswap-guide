---
title: "Ruby Logging Libraries: Lograge vs Semantic Logger vs Ruby Logger — Complete Guide 2026"
date: "2026-07-24"
tags: ["ruby", "rails", "logging", "observability", "lograge", "semantic-logger", "structured-logging", "ruby-logger"]
draft: false
---

## Introduction

Logging in Ruby applications starts simply — the standard library `Logger` class gets you up and running with `logger.info("Hello")`. But as your Rails application scales from a single server to a distributed system, plain-text logs become impossible to search, parse, and aggregate. Structured logging, log filtering, and asynchronous writes become essential for production observability.

The Ruby ecosystem offers three distinct approaches: the **built-in Logger** (stdlib, zero dependencies), **Lograge** (3,574 ⭐, tames Rails' verbose default output), and **Semantic Logger** (956 ⭐, enterprise-grade structured logging). This guide compares all three with real code examples and deployment patterns that work in production.

## Comparison at a Glance

| Feature | Ruby Logger (stdlib) | Lograge | Semantic Logger |
|---------|---------------------|---------|-----------------|
| **Type** | Built-in standard library | Rails log formatter | Full-featured logging framework |
| **Output Formats** | Plain text (customizable) | JSON, Logstash, KeyValue | JSON, Hash, Raw, Syslog, Graylog, Splunk, Elasticsearch |
| **Structured Logging** | Manual only | Automatic (request-level) | Full structured logging |
| **Async Logging** | No | No (depends on app server) | Yes (built-in async appender) |
| **Log Routing** | Single output | Per-controller configurable | Multiple appenders with level-based routing |
| **Rails Integration** | Default | Drop-in replacement | Full integration |
| **Performance** | Synchronous writes | Same as Logger | Async, buffered, high-performance |
| **Log Tagging** | Manual via `ActiveSupport::TaggedLogging` | Automatic request tagging | Built-in named tags and metrics |
| **GitHub Stars** | N/A (stdlib) | 3,574 | 956 |
| **Last Updated** | Bundled with Ruby | July 2026 | July 2026 |
| **License** | Ruby License | MIT | Apache 2.0 |

## Ruby Stdlib Logger: The Built-in Foundation

Ruby's standard library `Logger` is the default logging mechanism in Rails applications. It's simple, reliable, and requires zero configuration — but its default output is verbose and unstructured, making it painful to work with at scale.

### Basic Usage

```ruby
require 'logger'

# Standard setup
logger = Logger.new(STDOUT)
logger.level = Logger::INFO

logger.info("Application started")
logger.warn("Disk usage at 85%")
logger.error("Failed to connect to database: #{e.message}")

# With ActiveSupport::TaggedLogging (built into Rails)
logger = ActiveSupport::TaggedLogging.new(Logger.new(STDOUT))
logger.tagged("User-123") do
  logger.info("Processing order")
end
# Output: [User-123] Processing order
```

### Custom Format in Rails

```ruby
# config/environments/production.rb
config.log_formatter = Logger::Formatter.new

# Or use a custom JSON formatter
class JsonLogFormatter < Logger::Formatter
  def call(severity, time, progname, msg)
    {
      timestamp: time.iso8601,
      level: severity,
      message: msg.strip,
      pid: Process.pid
    }.to_json + "\n"
  end
end

config.log_formatter = JsonLogFormatter.new
```

### The Rails Log Problem

Rails' default logging is notoriously verbose. A single controller action generates multiple lines:

```
Started GET "/users/42" for 192.168.1.1 at 2026-07-24 10:30:00 +0000
Processing by UsersController#show as JSON
  Parameters: {"id"=>"42"}
  User Load (0.5ms)  SELECT "users".* FROM "users" WHERE "users"."id" = $1  [["id", 42]]
  ↳ app/controllers/users_controller.rb:15:in `show'
Completed 200 OK in 52ms (Views: 15.2ms | ActiveRecord: 0.5ms | Allocations: 2845)
```

In production with thousands of requests per minute, this becomes unmanageable. This is exactly the problem Lograge was built to solve.

### Strengths

- **Zero dependencies** — ships with Ruby itself
- **Simple API** — `debug`, `info`, `warn`, `error`, `fatal`
- **Rails defaults** — no setup needed in a new Rails app
- **TaggedLogging** — built-in context tagging via ActiveSupport

### Weaknesses

- **Verbose default output** — especially painful in Rails production logs
- **Synchronous writes** — blocks the request thread
- **No structured logging** — must build JSON formatting manually
- **Single output** — can't route different log levels to different destinations

## Lograge: Taming Rails Log Output

Lograge was created explicitly to solve Rails' verbose logging problem. Instead of multi-line request logs, Lograge condenses each HTTP request into a single, structured log line — making it dramatically easier to search and aggregate logs in tools like ELK, Datadog, and CloudWatch.

### Architecture

Lograge hooks into Rails' `ActionController::Instrumentation` and `ActionView::LogSubscriber` events. It intercepts the default logging pipeline and reformats the output into your chosen format — JSON, Logstash, or KeyValue — producing one line per request.

### Installation

```ruby
# Gemfile
gem 'lograge'
gem 'logstash-event'  # Only if using Logstash format
```

```bash
bundle install
```

### Basic Rails Setup

```ruby
# config/environments/production.rb
config.lograge.enabled = true

# JSON format (recommended for log aggregation)
config.lograge.formatter = Lograge::Formatters::Json.new

# Or Logstash format
# config.lograge.formatter = Lograge::Formatters::Logstash.new

# Customize which fields appear in the log line
config.lograge.custom_options = lambda do |event|
  {
    host: event.payload[:host],
    user_id: event.payload[:user_id],
    request_id: event.payload[:request_id],
    remote_ip: event.payload[:remote_ip],
    params: event.payload[:params]&.except('controller', 'action', 'format')
  }
end
```

### Before and After Lograge

**Before:** 5+ lines per request with SQL queries mixed in.

**After:** Single structured line:

```json
{
  "method": "GET",
  "path": "/users/42",
  "format": "json",
  "controller": "UsersController",
  "action": "show",
  "status": 200,
  "duration": 52.3,
  "view": 15.2,
  "db": 0.5,
  "host": "api.example.com",
  "remote_ip": "192.168.1.1",
  "user_id": 42
}
```

### Custom Configuration

```ruby
# config/environments/production.rb
config.lograge.enabled = true
config.lograge.formatter = Lograge::Formatters::Json.new

# Keep specific controller params
config.lograge.custom_payload do |controller|
  {
    tenant: controller.current_tenant&.name,
    feature_flags: Flipper.preload_all
  }
end

# Ignore specific actions (e.g., health checks)
config.lograge.ignore_actions = ['HealthController#show', 'StatusController#ping']

# Extract user info from controller
config.lograge.custom_options = lambda do |event|
  controller = event.payload[:controller_instance]
  {
    user_id: controller&.current_user&.id,
    organization_id: controller&.current_organization&.id
  }
end
```

### Strengths

- **One line per request** — revolutionary improvement over Rails defaults
- **Multiple output formats** — JSON, Logstash, KeyValue, custom
- **Zero performance overhead** — just reformats existing log data
- **Battle-tested** — used in thousands of Rails production apps
- **Selective logging** — filter out health checks and noisy endpoints

### Weaknesses

- **Request-level only** — doesn't help with background job logging
- **No async writes** — still writes synchronously through the Logger interface
- **Rails-specific** — not useful outside of Rails applications
- **No log routing** — single output destination

## Semantic Logger: Enterprise-Grade Structured Logging

Semantic Logger is a full-featured logging framework that replaces Ruby's standard Logger entirely. It supports asynchronous writes, multiple output destinations with level-based routing, built-in metrics collection, and structured data — making it the go-to choice for production systems where log performance and observability are critical.

### Architecture

Semantic Logger operates on a pipeline model: **Logger** → **Appender** → **Filter**. Each logger instance routes log messages through configurable filters before dispatching to one or more appenders (output destinations). The built-in async appender buffers log messages and writes them on a background thread, eliminating I/O blocking on request threads.

### Installation

```ruby
# Gemfile
gem 'semantic_logger'

# Optional: for Rails integration
# Already included automatically via Railtie
```

```bash
bundle install
```

### Basic Setup

```ruby
# config/initializers/semantic_logger.rb
require 'semantic_logger'

SemanticLogger.default_level = :info
SemanticLogger.application = "my-app"

# File appender with auto-rotation
SemanticLogger.add_appender(
  appender: :file,
  file_name: "log/#{Rails.env}.json",
  formatter: :json,
  level: :info
)

# Console appender for development
if Rails.env.development?
  SemanticLogger.add_appender(
    appender: :stream,
    stream: $stdout,
    formatter: :color,
    level: :debug
  )
end
```

### Structured Logging

```ruby
# Named logger
logger = SemanticLogger['UserService']

# Structured log with key-value pairs
logger.info("User logged in",
  user_id: 42,
  email: "user@example.com",
  ip_address: "192.168.1.1",
  authentication_method: "oauth"
)

# Log with duration tracking
logger.measure_info("Processing payment", payment_id: 789) do
  PaymentProcessor.charge!(amount: 99.99)
end
# Output: {"message":"Processing payment","payment_id":789,"duration":245.3,"level":"info"}

# Error logging with payload
begin
  ExternalService.call
rescue => e
  logger.error("External service failure",
    service: "PaymentGateway",
    attempt: 3,
    exception: e
  )
end
```

### Async + Multi-Destination Routing

```ruby
# Production configuration
SemanticLogger.add_appender(
  appender: :elasticsearch,
  url: ENV['ELASTICSEARCH_URL'],
  index: "logs-#{Rails.env}",
  level: :info
)

# Separate error log file
SemanticLogger.add_appender(
  appender: :file,
  file_name: "log/error.log",
  formatter: :json,
  level: :error
)

# Syslog for infrastructure alerts
SemanticLogger.add_appender(
  appender: :syslog,
  url: "tcp://syslog.internal:514",
  level: :warn
)

# Performance metrics to StatsD
SemanticLogger.on_log do |log|
  StatsD.increment("logs.#{log.level}") if log.metric
end
```

### Rails Integration

```ruby
# config/initializers/semantic_logger.rb
# Suppress noisy Rails logs
SemanticLogger.silence_log_level(
  "ActionView::Base",
  "ActiveRecord::LogSubscriber"
)

# Add request context to every log
SemanticLogger.on_log do |log|
  # Current request context is automatically added
  log.named_tags = {
    request_id: Thread.current[:request_id],
    tenant: Current.tenant
  }
end

# ApplicationController
class ApplicationController < ActionController::Base
  before_action :set_log_context

  private

  def set_log_context
    Thread.current[:request_id] = request.request_id
    SemanticLogger['Request'].info("Request started",
      method: request.method,
      path: request.path,
      user_agent: request.user_agent
    )
  end
end
```

### Strengths

- **Async appenders** — log writes never block request threads
- **Multiple output destinations** — split logs to Elasticsearch, files, and syslog simultaneously
- **Built-in metrics** — measure block durations with zero-code instrumentation
- **Level-based routing** — send errors to PagerDuty, info to Elasticsearch
- **Structured by design** — every log entry carries typed key-value pairs
- **Gem-wide configuration** — replace logging for all gems at once

### Weaknesses

- **Heavier** — 956 stars, smaller community than Lograge
- **Learning curve** — the pipeline model takes time to master
- **Overkill for small apps** — unnecessary for single-server deployments
- **Appender dependencies** — Elasticsearch, Syslog, and Splunk appenders require additional gems

## Deployment Patterns and Best Practices

### Lograge + ELK Stack

```yaml
# docker-compose.yml
version: "3.8"
services:
  rails:
    build: .
    environment:
      RAILS_ENV: production
      RAILS_LOG_TO_STDOUT: "true"
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  filebeat:
    image: elastic/filebeat:8.15.0
    volumes:
      - ./filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
      - rails_logs:/var/log/rails
    depends_on:
      - elasticsearch

  elasticsearch:
    image: elasticsearch:8.15.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9200:9200"

  kibana:
    image: kibana:8.15.0
    ports:
      - "5601:5601"

volumes:
  rails_logs:
```

### Semantic Logger with Elasticsearch

```ruby
# config/initializers/semantic_logger.rb (production)
require 'semantic_logger'

SemanticLogger.default_level = :info

# Elasticsearch for all application logs
SemanticLogger.add_appender(
  appender: :elasticsearch,
  url: ENV.fetch('ELASTICSEARCH_URL'),
  index: "rails-#{Rails.env}-%Y.%m.%d",
  level: :trace
)

# Rolling file as backup
SemanticLogger.add_appender(
  appender: :rolling_file,
  file_name: "log/production.log",
  max_size: 100 * 1024 * 1024,  # 100MB
  keep: 10,
  formatter: :json
)
```

## Why Self-Host Your Ruby Logging Infrastructure?

Owning your logging pipeline means you control log retention, format, and access — no third-party SaaS can suddenly change pricing or deprecate a feature critical to your debugging workflow. Open-source logging libraries let you build exactly the observability stack you need: structured JSON logs shipped to Elasticsearch or Loki, with retention policies that match your compliance requirements.

For testing patterns that integrate with logging, see our [Ruby testing frameworks guide](../2026-07-06-ruby-testing-frameworks-rspec-minitest-capybara/). For micro-framework deployments where logging configuration differs, check our [Ruby micro web frameworks comparison](../2026-07-06-ruby-micro-web-frameworks-sinatra-roda-grape/). If you're managing internal Ruby gems alongside your logging infrastructure, see our [self-hosted Ruby gem server guide](../2026-05-05-self-hosted-ruby-gem-servers-geminabox-gemstash-gem-in-a-box-guide/).

## FAQ

### Should I use Lograge or Semantic Logger for a new Rails 8 application?

For most new Rails applications, **start with Lograge**. It addresses the #1 pain point (verbose request logs) with minimal configuration — just add the gem and set `config.lograge.enabled = true`. Migrate to Semantic Logger when you need async writes (log I/O is becoming a bottleneck), multiple output destinations (e.g., Elasticsearch + file backup), or structured logging in background jobs (Sidekiq, GoodJob).

### How do I keep sensitive data out of my Ruby logs?

All three libraries support log filtering. In Rails, `config.filter_parameters` automatically filters `password`, `token`, and any keys you add before they reach the logging layer. For Lograge, the `custom_options` lambda lets you choose exactly what to include. For Semantic Logger, use a custom filter:

```ruby
SemanticLogger.add_appender(
  appender: :file,
  file_name: "log/production.json",
  filter: Proc.new { |log|
    log.payload.delete(:ssn)
    log.payload.delete(:credit_card)
    log  # Return the filtered log entry
  }
)
```

### Can I use Structured Logging without a gem like Semantic Logger?

Yes, but it requires more manual work. With the stdlib Logger and a custom formatter, you can output JSON:

```ruby
logger = Logger.new($stdout)
logger.formatter = proc do |severity, time, progname, msg|
  { time: time.iso8601, level: severity, message: msg&.strip }.to_json + "\n"
end
```

However, this only structures the top-level message — you lose the ability to attach arbitrary key-value pairs to log entries, which is Semantic Logger's core advantage. For production systems with more than a few services, the convenience of structured payloads in Semantic Logger pays for itself quickly.

### What logging approach works best with Docker/Kubernetes?

In containerized environments, **write structured JSON to stdout** and let your container runtime handle log shipping. Both Lograge (with JSON formatter) and Semantic Logger (with JSON appender to STDOUT) work well. The key practice: never write to local files in containers — always stream to stdout and use a log aggregator (Fluentd, Filebeat, Vector) to ship logs to your centralized store.

### Does Lograge affect Sidekiq or other background job log output?

No — Lograge only modifies request-level Rails logs. Background job logs from Sidekiq, GoodJob, or any ActiveJob adapter remain unchanged. If you want structured logging for background jobs too, Semantic Logger is the better choice since it replaces the global logging subsystem and automatically applies to all Ruby code in your process, including background workers.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Ruby Logging Libraries: Lograge vs Semantic Logger vs Ruby Logger — Complete Guide 2026",
  "description": "Comprehensive comparison of Ruby logging approaches: built-in Logger, Lograge (3.5K stars) for Rails request logging, and Semantic Logger (956 stars) for enterprise structured logging with async appenders and multi-destination routing.",
  "datePublished": "2026-07-24",
  "dateModified": "2026-07-24",
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
