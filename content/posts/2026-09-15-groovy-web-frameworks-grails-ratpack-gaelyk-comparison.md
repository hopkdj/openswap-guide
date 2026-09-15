---
title: "Groovy Web Frameworks in 2026: Grails vs Ratpack vs Gaelyk — Which One Still Ships?"
date: "2026-09-15"
tags: ["groovy", "web-frameworks", "jvm", "self-hosted", "comparison"]
draft: false
cover: "/img/screenshots/groovy-lang-logo.png"
---

Groovy is the language that quietly powers half the build scripts in the JVM world — and almost nobody picks it as the language for a new web service in 2026. That is a shame, because the three Groovy web stacks you can still deploy today occupy completely different points on the spectrum: **Grails** is a full Spring Boot application platform, **Ratpack** is a non-blocking Netty toolkit with a Groovy-first API, and **Gaelyk** is a ghost of the Google App Engine era. Two of them have shipped code in the last twelve months. One of them has not been touched since 2019.

Here is what the data actually says, plus the deployment configuration you need to run any of them in production.

## TL;DR — Quick Verdict

**Pick Grails if you want a full application platform.** It is the only one of the three with a current release (**v7.2.3**, August 2026) and a repository that receives commits almost daily. **Pick Ratpack if you are building a high-concurrency API** and you are comfortable with a slower release cadence — the framework is maintained, but its last tagged stable release is **1.9.0 from 2021**, with 1.10 milestones shipping since. **Do not pick Gaelyk.** It is a Google App Engine toolkit whose last commit was **June 2019**; the platform it targets does not exist in its original form anymore.

## Groovy Web Stack Comparison

| Dimension | **Grails 7** | **Ratpack 1.10** | **Gaelyk 2** |
|---|---|---|---|
| GitHub stars | 2,930 | 1,949 | 223 |
| Last commit | 2026-09-15 | 2026-07-03 | 2019-06-02 |
| Latest release | v7.2.3 (Aug 2026) | 1.9.0 (Jun 2021); 1.10.0 milestones | none (2.0-RC era) |
| HTTP foundation | Spring Boot 3 / embedded Tomcat | Netty event loop | App Engine servlet container |
| Programming model | Blocking + `async` GORM support | Non-blocking handlers | Groovlets + servlet spec |
| View layer | GSP (Groovy Server Pages) | None bundled (bring your own) | Groovy templates |
| Persistence | GORM (Hibernate, MongoDB, Neo4j) | None bundled (Guice/JDBC) | App Engine Datastore |
| Dependency injection | Spring | Optional Guice | None |
| License | Apache-2.0 | Apache-2.0 | Apache-2.0 |
| Production verdict | **Recommended** | Viable for APIs | Abandoned |

The stars are close between Grails and Ratpack, but stars are a lagging indicator. The forward-looking indicator is the release train: Grails shipped 7.2.3 in August 2026 on top of Spring Boot 3 and JDK 17+, while Ratpack's stable line has been frozen since 2021. That difference shows up the moment you need a security patch for a transitive dependency.

## Decision Matrix: Ten Seconds to a Decision

| Your Use Case | Recommended Tool | Why |
|---|---|---|
| CRUD app with admin screens, REST endpoints, and a database | **Grails 7** | GORM scaffolding turns a domain class into a working UI |
| High-concurrency JSON API on the JVM | **Ratpack** | Netty event loop, no thread-per-request overhead |
| Modernising an existing `war` deployment | Grails 7 | Ships an executable Spring Boot jar; no external container needed |
| A polyglot team already fluent in Spring | Grails 7 | Grails is Spring underneath, so Spring knowledge transfers |
| Running on legacy Google App Engine Java 8 | Gaelyk, then migrate | Groovlets still work; the platform support window does not |
| Greenfield project in 2026 | **Grails 7** | Everything else is either low-level or unmaintained |

## Grails — The Full Application Platform

Grails has been in production since 2008, and its distinguishing feature in 2026 is that it stopped trying to be different from Spring Boot and became a Groovy-flavoured layer on top of it. The official README states the requirements plainly: you need a JDK, but **Groovy is bundled with the distribution** — you do not install it separately. Set `GRAILS_HOME`, put it on your `PATH`, and you are two commands away from a running server:

```bash
# Official quickstart from the grails-core README
grails create-app sampleapp
cd sampleapp
grails run-app
```

A domain class plus scaffolding gives you a functional admin UI in minutes. That is the feature Ratpack and Gaelyk fundamentally lack:

```groovy
// grails-app/domain/sampleapp/Book.groovy
package sampleapp

class Book {
    String title
    String author
    Integer pages

    static constraints = {
        title blank: false, size: 1..200
        author blank: false
        pages nullable: true
    }
}

// grails-app/controllers/sampleapp/BookController.groovy
package sampleapp

class BookController {
    static scaffold = Book        // full CRUD UI generated at runtime
    static responseFormats = ['html', 'json']
}
```

Routing is declarative and lives in a single mappings file:

```groovy
// grails-app/controllers/sampleapp/UrlMappings.groovy
package sampleapp

class UrlMappings {
    static mappings = {
        "/books"(resources: "book")     // GET/POST/PUT/DELETE /books, /books/{id}
        "/health"(controller: "status", action: "health")
        "/"(view: "/index")
        "500"(view: '/error')
    }
}
```

Because Grails 7 is Spring Boot 3 underneath, packaging is the standard executable-jar story. Build the artifact in CI, then run it in a container with a JRE only:

```dockerfile
# ---- build stage ----
FROM eclipse-temurin:17-jdk AS build
WORKDIR /app
COPY gradlew gradlew
COPY gradle gradle
COPY build.gradle settings.gradle ./
RUN ./gradlew --no-daemon dependencies || true
COPY . .
RUN ./gradlew --no-daemon bootJar

# ---- runtime stage ----
FROM eclipse-temurin:17-jre
RUN groupadd -r app && useradd -r -g app app
WORKDIR /app
COPY --from=build /app/build/libs/*.jar /app/app.jar
USER app
EXPOSE 8080
ENV JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=75 -XX:+ExitOnOutOfMemoryError"
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
```

Notice `-XX:MaxRAMPercentage=75` instead of a hard `-Xmx`. The JVM is container-aware since JDK 10; a fixed heap in a container is how you get nodes killed by the OOM killer at 3 a.m.

### Self-Hosting Grails with Docker Compose

A Grails app plus PostgreSQL is the standard self-hosted shape. The database service uses the official `postgres` image, and the application talks to it by service name:

```yaml
services:
  db:
    image: postgres:17-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: grails_app
      POSTGRES_USER: grails
      POSTGRES_PASSWORD: change_me_in_env
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U grails -d grails_app"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    image: registry.example.com/grails-app:1.0.0
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    environment:
      SPRING_DATASOURCE_URL: jdbc:postgresql://db:5432/grails_app
      SPRING_DATASOURCE_USERNAME: grails
      SPRING_DATASOURCE_PASSWORD: change_me_in_env
      SPRING_PROFILES_ACTIVE: production
    ports:
      - "127.0.0.1:8080:8080"

volumes:
  pgdata:
```

Bind the port to `127.0.0.1` and put nginx or Caddy in front for TLS — the same reverse-proxy pattern used by any self-hosted JVM service. Expose only `/health` (Spring Boot Actuator's liveness endpoint) publicly, and keep `/actuator/env` and `/actuator/heapdump` behind a private network or disabled entirely.

## Ratpack — The Netty Toolkit for Groovy Developers

Ratpack describes itself as "a simple, capable, toolkit for creating high performance web applications," built on Java and the **Netty** event-driven engine, with an API "optimized for Groovy and Java 8." Where Grails abstracts the HTTP layer away, Ratpack *is* the HTTP layer — you compose handlers, and nothing generates code for you.

![Ratpack official project logo](/img/screenshots/ratpack-logo.png "Ratpack non-blocking web toolkit logo from the official repository")

A complete Ratpack application is a single script:

```groovy
// src/ratpack/Ratpack.groovy
import ratpack.groovy.Groovy.ratpack

ratpack {
    handlers {
        get {
            render "Hello from Groovy on Netty"
        }

        get("api/health") {
            render json([status: "ok", framework: "ratpack"])
        }

        get("api/books/:id") {
            def id = pathTokens["id"]
            render json([id: id, title: "The Pragmatic Programmer"])
        }

        // blocking work MUST run on the blocking pool, never on the event loop
        get("api/report") {
            blocking {
                render json([generated: new Date().toString()])
            }
        }
    }
}
```

Consume it with Gradle. Note the version situation honestly: the last stable tag is `1.9.0` (June 2021), while current development publishes milestones, for example `1.10.0-milestone-39` as seen on Maven Central:

```groovy
// build.gradle
plugins {
    id 'io.ratpack.ratpack-groovy' version '2.0.0-rc-1'
}

repositories { mavenCentral() }

dependencies {
    implementation ratpack.dependency('groovy')
    implementation 'io.ratpack:ratpack-guice:1.9.0'    // optional DI
    implementation 'ch.qos.logback:logback-classic:1.5.6'
}

ratpack {
    handlers {
        // handler definitions can live in the build file during prototyping
    }
}
```

The one rule that trips up every newcomer: **never block the event loop.** A JDBC call directly inside a handler stalls every other request on that Netty thread. Ratpack gives you `blocking { }` precisely for this, and it is not optional when you touch a database.

A practical deployment packages the app as a fat jar and runs it on a JRE:

```dockerfile
FROM gradle:8-jdk17 AS build
WORKDIR /src
COPY . .
RUN gradle --no-daemon shadowJar

FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=build /src/build/libs/*-all.jar /app/app.jar
RUN useradd -r app && chown -R app /app
USER app
EXPOSE 5050
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75", "-jar", "/app/app.jar"]
```

Ratpack's default port is **5050**, not 8080 — a small detail that generates a surprising number of "the container is running but nothing responds" bug reports.

## Gaelyk — What Abandonment Looks Like

Gaelyk was "a lightweight Groovy toolkit for Google App Engine Java": Groovlets for quick endpoints, Groovy templates for views, and first-class access to Datastore. For its era it was genuinely pleasant. Its last commit is **2019-06-02**, the runtime it targeted (App Engine Java 8 with the original Datastore APIs) has been superseded, and there is no upgrade path that does not involve rewriting the application. If you inherit a Gaelyk codebase, treat it as a migration project with a deadline, not a platform to extend. The good news is that Gaelyk applications are usually small, and Grails 7 or a plain Spring Boot service absorbs them cleanly.

## Deployment Pitfalls for Groovy Stacks

**1. Groovy version conflicts across the toolchain.** Grails bundles Groovy and manages it through Gradle. Mixing a globally installed Groovy with a project's wrapper is the fastest way to non-reproducible builds. Always commit the Gradle wrapper (`gradle wrapper`) and build through it.

**2. Container memory is not a JVM setting you can ignore.** Set `-XX:MaxRAMPercentage` and add `-XX:+ExitOnOutOfMemoryError` so a leaking container dies and restarts instead of thrashing the host.

**3. GORM lazy loading hides N+1 queries.** Scaffolding makes development delightful and production slow. Fetch-plan your associations (`static mapping = { author fetch: 'join' }`) before you blame the database.

**4. Ratpack's release cadence is a supply-chain decision.** Stable tags stopped at 1.9.0. Before adopting it for a long-lived service, decide whether you are willing to run milestones or vendor and patch a stable build yourself.

**5. Never block Ratpack's event loop.** Use `blocking { }` for any JDBC, filesystem, or third-party HTTP call. One blocking handler can degrade an entire Netty event loop.

**6. Prefer a JRE runtime image, not a JDK.** The JRE cuts image size by hundreds of megabytes and removes `javac` from your production attack surface.

## Related Reading

If you are choosing a JVM stack rather than a Groovy-specific one, our [Java web framework comparison](../2026-07-03-java-web-frameworks-spring-boot-quarkus-micronaut-helidon-javalin/) covers the same tradeoffs in plain Java, and the [JVM reactive libraries guide](../2026-08-10-java-reactive-libraries-project-reactor-rxjava-vertx-guide/) explains the non-blocking model Ratpack implements with Netty. For a compiled-language alternative with a much smaller runtime footprint, see the [D web framework comparison](../2026-09-15-d-web-frameworks-vibe-d-hunt-diamond-comparison/) published alongside this article.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Groovy Web Frameworks in 2026: Grails vs Ratpack vs Gaelyk — Which One Still Ships?",
  "description": "Live-data comparison of Groovy web frameworks Grails 7, Ratpack and Gaelyk, with Dockerfiles, docker-compose for PostgreSQL, GORM scaffolding examples, release-cadence risks and a use-case decision matrix.",
  "datePublished": "2026-09-15",
  "dateModified": "2026-09-15",
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

## FAQ

**Is Grails still worth learning in 2026?**
Yes, if your work involves JVM CRUD applications. Grails 7.2.3 shipped in August 2026 and the project receives commits continuously. Because Grails is Spring Boot with a Groovy layer, the skills transfer directly: GORM builds on Hibernate, the container is embedded Tomcat, and configuration is Spring's. You get convention-over-configuration scaffolding without leaving the Spring ecosystem.

**Why does Ratpack not have a stable release since 2021?**
The project publishes milestones on the 1.10 line (for example `1.10.0-milestone-39` on Maven Central) rather than cutting stable tags. The code is maintained — commits landed in July 2026 — but if your procurement rules require stable releases, you should either pin `1.9.0` and vendor patches or choose a differently governed framework.

**Can I run Gaelyk applications off Google App Engine?**
Technically the Groovlets are servlet-based, so you can host them in a standalone servlet container, but you lose Datastore, the task queues, and the user service that most Gaelyk code depends on. Combined with a final commit in 2019, migration to Grails or Spring Boot is almost always cheaper than adaptation.

**How should I size a JVM container for a Groovy application?**
Set `-XX:MaxRAMPercentage=75` rather than a fixed `-Xmx`, add `-XX:+ExitOnOutOfMemoryError`, and give the container a real memory limit. Groovy's dynamic dispatch creates more short-lived objects than equivalent Java code, so enable container-aware GC logging during load tests before tuning anything else.

**Does Grails work with PostgreSQL and MySQL self-hosted?**
Yes. GORM's Hibernate dialect supports PostgreSQL, MySQL/MariaDB, Oracle, and SQL Server, and the Spring Boot datasource is configured with standard `SPRING_DATASOURCE_*` environment variables. The docker-compose example above uses the official `postgres:17-alpine` image with a healthcheck so the application does not start before the database accepts connections.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
