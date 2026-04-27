---
title: "Apache Tomcat vs WildFly vs Gunicorn: Self-Hosted Application Servers 2026"
date: 2026-04-27
tags: ["comparison", "guide", "self-hosted", "java", "python", "deployment"]
draft: false
description: "Compare Apache Tomcat, WildFly, and Gunicorn — three popular open-source application servers for self-hosted web applications. Includes Docker configs, performance benchmarks, and deployment guides."
---

When deploying web applications on your own infrastructure, choosing the right application server is critical. The application server sits between your code and the network, handling HTTP requests, managing connections, and executing your application logic. Three of the most widely used open-source options are **Apache Tomcat**, **WildFly**, and **Gunicorn** — each serving different ecosystems and use cases.

This guide compares these three application servers across performance, features, ease of deployment, and resource consumption to help you pick the right one for your self-hosted environment.

For related reading, see our [Nginx vs Caddy vs Traefik web server comparison](../nginx-vs-caddy-vs-traefik-self-hosted-web-server-guide/) and [Nginx Proxy Manager vs SWAG vs Caddy reverse proxy guide](../2026-04-24-nginx-proxy-manager-vs-swag-vs-caddy-docker-proxy-self-hosted-reverse-proxy-gui-guide-2026/) for understanding how to route traffic to your application server.

## Why Self-Host Your Application Server?

Running your own application server gives you full control over your deployment stack:

- **No vendor lock-in** — you own the infrastructure and can migrate at will
- **Data sovereignty** — application logs, session data, and metrics stay on your servers
- **Cost predictability** — fixed infrastructure costs instead of per-request pricing
- **Custom configurations** — tune thread pools, connection limits, and JVM/interpreter settings to your workload
- **Network isolation** — deploy behind your own reverse proxy, WAF, and load balancer

Whether you are serving Java servlets, Jakarta EE applications, or Python web frameworks, having a dedicated application server that you fully control is a foundational building block of self-hosted infrastructure.

## Apache Tomcat

[Apache Tomcat](https://tomcat.apache.org/) is the most widely deployed Java application server in the world. It implements the Jakarta Servlet, Jakarta Server Pages (JSP), and WebSocket specifications. As of April 2026, the [apache/tomcat](https://github.com/apache/tomcat) repository has over 8,100 stars and is actively maintained.

Tomcat is designed to be lightweight and focused. Unlike full Java EE servers, it does not implement Enterprise JavaBeans (EJB) or JMS — it specializes in serving web applications (WAR files) efficiently.

### Key Features

- Implements Jakarta Servlet 6.0, JSP 3.1, WebSocket 2.1, and Expression Language 5.0
- Embedded mode available for Spring Boot and other frameworks
- JMX management and monitoring
- Valve-based request processing pipeline
- Realm-based authentication (JDBC, LDAP, JAAS, memory)
- Hot-reload of WAR files without server restart

### Installation

**Package manager (Debian/Ubuntu):**

```bash
apt update
apt install tomcat10 tomcat10-admin tomcat10-user
systemctl enable tomcat10
systemctl start tomcat10
```

**Docker Compose:**

```yaml
version: "3.8"
services:
  tomcat:
    image: tomcat:10.1-jre21
    ports:
      - "8080:8080"
    volumes:
      - ./webapps:/usr/local/tomcat/webapps
      - ./conf:/usr/local/tomcat/conf
    environment:
      - JAVA_OPTS=-Xms256m -Xmx512m -XX:+UseG1GC
    restart: unless-stopped
```

**Docker with manager access:**

```yaml
version: "3.8"
services:
  tomcat:
    image: tomcat:10.1-jre21
    ports:
      - "8080:8080"
      - "8081:8080"
    volumes:
      - ./webapps:/usr/local/tomcat/webapps
    command: >
      bash -c "
        cp -r /usr/local/tomcat/webapps.dist/* /usr/local/tomcat/webapps/ &&
        /usr/local/tomcat/bin/catalina.sh run
      "
    restart: unless-stopped
```

### Performance Characteristics

Tomcat uses a thread-pool model with configurable connector settings. For production deployments:

```xml
<!-- server.xml connector tuning -->
<Connector port="8080" protocol="org.apache.coyote.http11.Http11NioProtocol"
           maxThreads="200"
           minSpareThreads="25"
           maxConnections="10000"
           acceptCount="100"
           connectionTimeout="20000"
           compression="on"
           compressibleMimeType="text/html,text/xml,text/plain,application/json"
           URIEncoding="UTF-8" />
```

Typical memory footprint: 256-512 MB heap for moderate workloads. Handles 5,000-15,000 requests per second depending on application complexity and hardware.

## WildFly (Formerly JBoss AS)

[WildFly](https://www.wildfly.org/) is a full-featured Jakarta EE application server maintained by Red Hat. With over 3,100 GitHub stars on [wildfly/wildfly](https://github.com/wildfly/wildfly), it is the open-source upstream for Red Hat JBoss Enterprise Application Platform.

Unlike Tomcat, WildFly implements the complete Jakarta EE specification, including EJB, JMS, JTA, CDI, JPA, and more. It is the right choice when you need enterprise-grade features beyond servlets.

### Key Features

- Full Jakarta EE 10 certification
- Elytron security subsystem (unified security framework)
- Undertow HTTP server (high-performance, non-blocking)
- Domain mode for managing multiple server instances from a central controller
- Hot deployment and rollback
- Built-in clustering and session replication
- Management CLI and web console
- MicroProfile support for cloud-native Java

### Installation

**Package manager (RHEL/Fedora):**

```bash
dnf install wildfly
systemctl enable wildfly
systemctl start wildfly
```

**Docker Compose:**

```yaml
version: "3.8"
services:
  wildfly:
    image: quay.io/wildfly/wildfly:33.0.0.Final-jdk21
    ports:
      - "8080:8080"
      - "9990:9990"
    volumes:
      - ./deployments:/opt/jboss/wildfly/standalone/deployments
      - ./configuration:/opt/jboss/wildfly/standalone/configuration
    environment:
      - JAVA_OPTS=-Xms512m -Xmx1024m -XX:+UseG1GC
      - ADMIN_USERNAME=admin
      - ADMIN_PASSWORD=change-me
    restart: unless-stopped
```

**Docker with management console:**

```yaml
version: "3.8"
services:
  wildfly:
    image: quay.io/wildfly/wildfly:33.0.0.Final-jdk21
    ports:
      - "8080:8080"
      - "9990:9990"
    environment:
      - WILDFLY_ADMIN_USERNAME=admin
      - WILDFLY_ADMIN_PASSWORD=SecurePass123!
      - JAVA_OPTS=-Xms512m -Xmx1024m
    command: >
      /opt/jboss/wildfly/bin/standalone.sh
      -b 0.0.0.0
      -bmanagement 0.0.0.0
    restart: unless-stopped
```

### Performance Characteristics

WildFly's Undertow HTTP server delivers excellent performance for a full EE server. The management overhead (domain mode, clustering) adds to the baseline resource usage.

Typical memory footprint: 512 MB - 1 GB heap minimum. Throughput of 3,000-10,000 requests per second depending on EE features used. Domain mode adds ~200 MB overhead per managed server instance.

## Gunicorn

[Gunicorn](https://gunicorn.org/) (Green Unicorn) is a Python WSGI HTTP server. With over 10,500 stars on [benoitc/gunicorn](https://github.com/benoitc/gunicorn), it is the most popular production-grade Python application server.

Unlike Tomcat and WildFly, Gunicorn is not a Java server — it serves Python web applications built on frameworks like Django, Flask, FastAPI, and Pyramid. It uses a pre-fork worker model and is designed for UNIX environments.

### Key Features

- Pre-fork worker model with multiple worker types (sync, gevent, eventlet, uvicorn workers)
- Graceful reload and hot code upgrades without dropping connections
- Automatic worker crash recovery
- Configurable worker timeout and keepalive
- Integration with systemd socket activation
- Low memory footprint compared to JVM-based servers
- Native support for WSGI applications

### Installation

**pip:**

```bash
pip install gunicorn
```

**Docker Compose with Django:**

```yaml
version: "3.8"
services:
  web:
    build: .
    command: gunicorn myproject.wsgi:application --bind 0.0.0.0:8000 --workers 4 --threads 2
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    environment:
      - DJANGO_SETTINGS_MODULE=myproject.settings
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
```

**Docker Compose with FastAPI:**

```yaml
version: "3.8"
services:
  api:
    image: python:3.12-slim
    working_dir: /app
    volumes:
      - .:/app
    command: >
      bash -c "
        pip install fastapi uvicorn gunicorn &&
        gunicorn app:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 -w 4
      "
    ports:
      - "8000:8000"
    restart: unless-stopped
```

**Production Gunicorn configuration file (`gunicorn.conf.py`):**

```python
# gunicorn.conf.py
import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"

# Process naming
proc_name = "gunicorn_prod"

# Graceful timeout for restarts
graceful_timeout = 30
```

### Performance Characteristics

Gunicorn's pre-fork model is lightweight and efficient. Memory per worker varies by framework — a Django worker typically uses 80-150 MB, while a minimal Flask worker uses 30-50 MB.

Throughput: 1,000-5,000 requests per second per worker with sync mode. With async workers (uvicorn/gevent), this can reach 10,000-20,000+ rps for I/O-bound workloads.

## Comparison Table

| Feature | Apache Tomcat 10 | WildFly 33 | Gunicorn 22 |
|---|---|---|---|
| **Language** | Java | Java | Python |
| **Specification** | Jakarta Servlet, JSP, WebSocket | Full Jakarta EE 10 | WSGI (PEP 3333) |
| **GitHub Stars** | 8,154 | 3,160 | 10,556 |
| **Memory Footprint** | 256-512 MB | 512 MB - 1 GB | 30-150 MB per worker |
| **Throughput (rps)** | 5,000-15,000 | 3,000-10,000 | 1,000-20,000+ |
| **Hot Deployment** | Yes (WAR) | Yes (EAR/WAR/JAR) | Yes (via graceful reload) |
| **Management UI** | Tomcat Manager | WildFly Admin Console | None (CLI only) |
| **Clustering** | Limited (session replication) | Full (domain mode) | Via external load balancer |
| **Embedded Mode** | Yes | Yes (WildFly Swarm) | Yes (as library) |
| **Security** | Realms, JAAS | Elytron subsystem | Basic auth, SSL |
| **JMX Monitoring** | Yes | Yes | No (external tools needed) |
| **Docker Image Size** | ~350 MB | ~600 MB | ~150 MB (slim Python) |
| **Best For** | Java web apps, Spring Boot | Enterprise Java, Jakarta EE | Django, Flask, FastAPI |

## When to Choose Each Server

### Choose Apache Tomcat When:

- You are deploying Java web applications (WAR files)
- You need Servlet/JSP support without full Jakarta EE overhead
- You want a battle-tested server with decades of production use
- You are using Spring Boot's embedded Tomcat and want to externalize it
- You need JMX-based monitoring and management

### Choose WildFly When:

- Your application uses EJB, JMS, JTA, or other Jakarta EE components
- You need domain mode to manage multiple server instances centrally
- You require built-in clustering, session replication, and load balancing
- You are migrating from JBoss EAP and want the open-source equivalent
- You need MicroProfile support alongside full Jakarta EE

### Choose Gunicorn When:

- You are deploying Python web applications (Django, Flask, FastAPI)
- You need a lightweight server with minimal memory overhead
- You want to use async workers for high-concurrency I/O-bound workloads
- You are containerizing Python apps and want small Docker images
- You prefer simplicity over feature richness

## Production Architecture Patterns

### Pattern 1: Tomcat Behind Nginx

```
Client → Nginx (reverse proxy, TLS termination) → Tomcat (application logic)
```

```nginx
upstream tomcat_backend {
    server 127.0.0.1:8080;
}

server {
    listen 443 ssl http2;
    server_name app.example.com;

    ssl_certificate /etc/ssl/certs/app.crt;
    ssl_certificate_key /etc/ssl/private/app.key;

    location / {
        proxy_pass http://tomcat_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /var/www/app/static/;
        expires 30d;
    }
}
```

### Pattern 2: WildFly Domain Mode

```
                  ┌─ WildFly Server 1 (app node)
Load Balancer ───┼─ WildFly Server 2 (app node)
                  ├─ WildFly Server 3 (app node)
                  └─ Domain Controller (management)
```

Start domain controller:

```bash
/opt/wildfly/bin/domain.sh --host-config=host-master.xml
```

Start managed servers:

```bash
/opt/wildfly/bin/domain.sh --host-config=host-slave.xml \
    -Djboss.domain.master.address=10.0.0.1
```

### Pattern 3: Gunicorn with Systemd

Create `/etc/systemd/system/gunicorn.service`:

```ini
[Unit]
Description=Gunicorn application server
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/myapp
Environment="PATH=/var/www/myapp/venv/bin"
ExecStart=/var/www/myapp/venv/bin/gunicorn \
    --config /etc/gunicorn/gunicorn.conf.py \
    myapp.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable gunicorn
systemctl start gunicorn
systemctl status gunicorn
```

## Security Hardening

### Tomcat Security

```xml
<!-- conf/server.xml: Disable unnecessary connectors -->
<!-- Remove or comment out the AJP connector if not used -->
<!-- <Connector port="8009" protocol="AJP/1.3" redirectPort="8443" /> -->

<!-- conf/web.xml: Disable directory listings -->
<init-param>
    <param-name>listings</param-name>
    <param-value>false</param-value>
</init-param>

<!-- conf/tomcat-users.xml: Use strong passwords, limit roles -->
<role rolename="manager-gui"/>
<user username="admin" password="${CATALINA_BASE}/conf/.tomcat-admin-pwd" roles="manager-gui"/>
```

### WildFly Security

```bash
# Use Elytron for authentication
./jboss-cli.sh --connect \
    "/subsystem=elytron/filesystem-realm=app-realm:add(path=app-users,relative-to=jboss.server.config.dir)"

./jboss-cli.sh --connect \
    "/subsystem=elytron/security-domain=app-domain:add(realms=[{realm=app-realm}],default-realm=app-realm,permission-mapper=default-permission-mapper)"
```

### Gunicorn Security

```python
# gunicorn.conf.py - security settings
# Run as non-root user
user = "www-data"
group = "www-data"

# Limit request size to prevent DoS
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Bind to localhost only (use reverse proxy for external access)
bind = "127.0.0.1:8000"

# Chroot for additional isolation
# chroot = "/var/www/myapp/chroot"
```

## FAQ

### Can Tomcat run Python applications?

No. Apache Tomcat is a Java-based server that implements the Jakarta Servlet specification. It can only run Java web applications packaged as WAR files. For Python applications, use Gunicorn or another WSGI/ASGI server.

### Is WildFly compatible with Spring Boot?

Yes, but with caveats. WildFly can deploy Spring Boot applications, but Spring Boot is designed primarily for embedded servers (Tomcat, Jetty, Undertow). For WildFly, you should package as a WAR and exclude the embedded server from Spring Boot's dependencies.

### Can Gunicorn handle WebSocket connections?

Not natively. Gunicorn is a WSGI server and the WSGI specification does not support WebSocket. For WebSocket in Python, use an ASGI server like Uvicorn or Daphne. You can use Gunicorn with Uvicorn workers (`-k uvicorn.workers.UvicornWorker`) for ASGI applications like FastAPI that include WebSocket support.

### Which application server uses the least memory?

Gunicorn is the lightest by a significant margin. A single Gunicorn worker running a Flask app uses approximately 30-50 MB of RAM, while Tomcat needs at least 256 MB and WildFly 512 MB minimum due to JVM overhead and EE subsystem initialization.

### Can I run multiple applications on a single server instance?

Tomcat supports multiple web applications via separate WAR files in the `webapps/` directory. WildFly can deploy multiple EAR/WAR files simultaneously with isolation between deployments. Gunicorn runs one Python application per instance — for multiple Python apps, run separate Gunicorn processes behind a reverse proxy.

### How do I monitor these servers in production?

Tomcat provides JMX metrics accessible via JConsole or VisualVM. WildFly offers a comprehensive management console at port 9990 and CLI access. Gunicorn has no built-in monitoring — use external tools like Prometheus with the `gunicorn-exporter` or integrate with your logging stack (ELK, Loki). For all three, reverse proxy access logs provide request-level visibility.

### Do these servers support automatic SSL/TLS termination?

None of them handle SSL/TLS termination natively in recommended production setups. The standard pattern is to place a reverse proxy (Nginx, Caddy, or Traefik) in front of the application server to handle TLS termination, HTTP/2, and load balancing. Caddy can auto-provision Let's Encrypt certificates, making it the simplest option for SSL management.

### Can these servers run inside Docker containers?

Yes, all three have official Docker images. Tomcat and WildFly provide images with pre-configured JVM settings. Gunicorn is typically run in a custom Docker image that bundles your Python application. For production, always set resource limits (`--memory`, `--cpus`) on Docker containers and configure health checks.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Apache Tomcat vs WildFly vs Gunicorn: Self-Hosted Application Servers 2026",
  "description": "Compare Apache Tomcat, WildFly, and Gunicorn — three popular open-source application servers for self-hosted web applications. Includes Docker configs, performance benchmarks, and deployment guides.",
  "datePublished": "2026-04-27",
  "dateModified": "2026-04-27",
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
