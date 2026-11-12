---
title: "UniTime vs Timefold vs FET in 2026: Which Open-Source Timetabling Engine Actually Fits Your Institution?"
date: "2026-11-12"
tags: ["scheduling", "open-source", "self-hosted", "operations-research", "education"]
draft: false
description: "A hands-on comparison of the three serious open-source timetabling stacks: UniTime's institutional platform, the Timefold constraint solver, and FET's offline generator - with real Docker configs, deployment pitfalls, and a decision matrix."
---

Every semester, somebody at a university spends two to three weeks moving coloured blocks around a spreadsheet while 4,000 students wait for a schedule. The combinatorics are brutal: a mid-sized institution with 400 courses, 60 rooms and 25 timeslots has on the order of 10^40 nominal assignments, of which maybe a few thousand satisfy hard constraints like "Professor Chen cannot teach two rooms at once."

Commercial timetabling suites charge per-student licensing for solving this. Three open-source projects solve it for free, and they are **not** interchangeable: one is a full institutional platform, one is a Java constraint engine you embed in your own service, and one is a desktop generator that finishes in ninety seconds. Picking the wrong one costs you a semester. This guide compares all three on real deployment mechanics, not marketing pages.

## TL;DR

- **You are a registrar or IT team at a school/university and want a web UI, student course requests, exam scheduling and multi-campus support** → **UniTime**. It is the only one of the three that is a complete timetabling *system*.
- **You are a developer and timetabling is one feature inside a larger application (rostering, exams, bus routing, factory shifts)** → **Timefold Solver**. You model constraints in Java or Kotlin and get a solver, not a UI.
- **You need a printable timetable by Friday, you have no DBA, and your data lives in spreadsheets** → **FET**. Single binary, no database, no server, XML in and XML out.

If you deploy UniTime expecting a solver library you will fight it for weeks. If you deploy FET expecting a multi-user web platform you will hit a wall on day two. The failure mode is always a mismatch of *category*, not of quality.

## Side-by-side comparison

| Dimension | UniTime | Timefold Solver | FET |
|---|---|---|---|
| GitHub stars | 358 | 1,867 | Not on GitHub (released on lalescu.ro / SourceForge) |
| Primary language | Java | Java / Kotlin | C++ (Qt) |
| License | Apache-2.0 (Apereo Foundation) | Apache-2.0 | GPL-2.0+ |
| Deployment model | Tomcat + MySQL, official Docker compose | Library dependency (Maven/Gradle), Quarkus/Spring Boot samples | Desktop app + `fet-cl` headless CLI |
| Database required | MySQL | None (your model lives in your app) | None (XML data file) |
| Web UI | Yes, full administrative UI | No (bring your own) | Desktop GUI, HTML export |
| Multi-user | Yes, roles, departments, student course requests | No (embedded) | Single operator |
| Hard/soft constraint model | Fixed, domain-specific | Fully programmable in code | Configurable weights in the GUI/XML |
| Last commit (checked) | 2026-11-12 | 2026-11-11 | Active 7.x series |
| Realistic time to first timetable | 2-6 weeks | 1-3 days for a developer | 1-2 days |

## Decision matrix

| Your situation | Pick | Why |
|---|---|---|
| 5,000 students, 12 departments, exam weeks | UniTime | Course requests, departmental permissions and exam scheduling are built in |
| You are shipping a rostering feature in a SaaS product | Timefold | Apache-2.0, embeddable, constraint streams in plain Java |
| A single faculty needs a schedule once a semester | FET | No database, no server, printable output |
| You need vehicle routing *and* timetabling in one codebase | Timefold | Same engine solves both (VRP and planning) |
| You have no Linux admin and only Windows desktops | FET | Installs like a normal desktop program |
| You want to expose a public API for timetabling | UniTime or Timefold | UniTime has a web layer; Timefold gives you the engine to wrap |

## UniTime — the full institutional platform

UniTime is the one project here that behaves like enterprise software because it *is* enterprise software: it has been deployed at universities across North America and Europe for close to two decades, and it is governed by the Apereo Foundation, the same organization behind Sakai.

What you get out of the box:

- **Course timetabling** across multiple campuses and terms, with room and instructor constraints.
- **Student course requests** — students rank the sections they want, and UniTime optimises section assignment against those preferences.
- **Examination timetabling** with conflict matrices, back-to-back rules and room capacity handling.
- **Event management** for ad-hoc bookings that must not collide with classes.
- **Role-based access** so a department scheduler can only touch their own courses.

The deployment is a two-container stack: MySQL and Tomcat. The repository ships a working compose file under `Documentation/Docker/`, which is the sane starting point:

```yaml
services:
    unitime-db:
        container_name: unitime-db
        command: --default-authentication-plugin=mysql_native_password
        environment:
            - MYSQL_RANDOM_ROOT_PASSWORD=yes
            - MYSQL_USER=timetable
            - MYSQL_PASSWORD=unitime
            - MYSQL_DATABASE=timetable
        volumes:
            - "unitime-db:/var/lib/mysql"

    unitime-web:
        container_name: unitime-web
        depends_on:
            - unitime-db
        environment:
            - JAVA_OPTS=-Dconnection.url=jdbc:mysql://unitime-db:3306/timetable
        ports:
            - "8080:8080"
```

Two things bite people here. First, the images are **built locally** from `mysql.Dockerfile` and `tomcat.Dockerfile`; there is no official prebuilt image, so a first `docker compose up --build` takes a while and needs network access for the Maven and package downloads. Second, `MYSQL_RANDOM_ROOT_PASSWORD=yes` means you must read the generated root password from the container logs (`docker logs unitime-db | grep -i "GENERATED ROOT PASSWORD"`) before you can run any administrative SQL.

UniTime's honest weakness: **the constraint model is opinionated**. If your institution has a rule nobody else has — say, "no lab session may start in the same building as a lecture that ends five minutes earlier" — you may end up modifying Java rather than editing a config file. Budget for a developer who can read Hibernate mappings if your requirements are unusual.

## Timefold Solver — the embeddable constraint engine

Timefold is the actively maintained successor to OptaPlanner: same author lineage, cleanly relicensed, and now the fastest-moving project of the three with **1,867 stars and commits landing daily**. It is *not* a timetabling application. It is a constraint solver with a planning model, and timetabling is one of the problem shapes it handles well.

The programming model is annotation-driven. You declare which field is the planning variable, supply a value range, and write constraints as streams:

```java
@PlanningEntity
public class Lecture {

    @PlanningVariable(valueRangeProviderRefs = "timeslotRange")
    private Timeslot timeslot;

    @PlanningVariable(valueRangeProviderRefs = "roomRange")
    private Room room;
}
```

Constraints are code, which is the whole point:

```java
public Constraint[] defineConstraints(ConstraintFactory factory) {
    return new Constraint[] {
        // Hard: a room hosts at most one lecture per timeslot
        factory.forEachUniquePair(Lecture.class,
                Joiners.equal(Lecture::getRoom),
                Joiners.equal(Lecture::getTimeslot))
            .penalize(HardSoftScore.ONE_HARD)
            .asConstraint("Room conflict"),

        // Hard: an instructor cannot be in two rooms at once
        factory.forEachUniquePair(Lecture.class,
                Joiners.equal(Lecture::getInstructor),
                Joiners.equal(Lecture::getTimeslot))
            .penalize(HardSoftScore.ONE_HARD)
            .asConstraint("Instructor conflict"),

        // Soft: avoid 8am starts
        factory.forEach(Lecture.class)
            .filter(l -> l.getTimeslot().getStartHour() < 9)
            .penalize(HardSoftScore.ONE_SOFT)
            .asConstraint("Early start")
    };
}
```

Add the solver as a dependency (`timefold-solver-core` on Maven Central) and run it:

```java
SolverFactory<CourseSchedule> factory = SolverFactory.create(
    new SolverConfig()
        .withSolutionClass(CourseSchedule.class)
        .withEntityClasses(Lecture.class)
        .withConstraintProviderClass(TimetableConstraintProvider.class)
        .withTerminationSpentLimit(Duration.ofMinutes(2)));

CourseSchedule solved = factory.buildSolver().solve(problem);
```

This is where Timefold earns its stars: two minutes of solver time on a 400-lecture problem typically produces a schedule with **zero hard-constraint violations** and a soft score you can tune by reweighting constraints in code. The catch is that you own everything around it — data model, persistence, authentication, UI, and the explanation of *why* a schedule is bad (which registrars always ask).

Do not underestimate that last part. UniTime ships screens that explain conflicts; with Timefold you build them.

## FET — the offline generator that still wins on simplicity

FET (Free Timetabling Software) is the pragmatic outlier: a Qt desktop application by Liviu Lalescu, available in Debian and Ubuntu repositories, with a headless command-line companion called `fet-cl`. It has **no database, no server, and no login**. Your entire problem is one XML file.

Installing it on a Debian/Ubuntu workstation or server is a one-liner:

```bash
sudo apt update && sudo apt install -y fet
fet-cl --version
```

The headless workflow is what makes FET usable in automation:

```bash
# Generate a timetable from an existing data file, 20 seconds budget
fet-cl --inputfile=school.fet --outputdir=out --timelimitseconds=20
```

And the generated `.fet` file is plain XML, so you can generate it from your student information system with a script instead of clicking through the GUI:

```xml
<Activities_List>
    <Activity>
        <Teacher>Chen</Teacher>
        <Subject>Algorithms</Subject>
        <Students>CS-Year2</Students>
        <Duration>2</Duration>
        <Total_Duration>2</Total_Duration>
        <Id>101</Id>
        <Activity_Group_Id>0</Activity_Group_Id>
    </Activity>
</Activities_List>
```

FET's constraint system covers the practical 90%: teacher and student set conflicts, room preferences, min/max days between activities, and activity tags for "this lab needs a projector room". Its solver is single-threaded and old-fashioned compared to Timefold, but for a single faculty with 60 activities it finishes in seconds.

Where FET breaks: **anything multi-user**. No concurrent editors, no permissions, no audit trail, no API. If two people need to touch the data, you are back to emailing XML files. It also does not scale gracefully to 5,000-activity university problems — expect long runs and manual constraint relaxation.

## Deployment pitfalls worth knowing before you start

1. **UniTime's Docker build is not a pull-and-run.** Plan for a 10-20 minute first build and pin the MySQL image tag; an unexpected MySQL 9 upgrade will break the native password authentication flag used in the compose file.
2. **Timefold scores are only comparable within one constraint set.** Team A's `-1200` soft score is meaningless next to Team B's `-40`. Publish the constraint weights alongside the score or you will argue about nothing.
3. **FET's XML is strict about IDs.** Duplicate `Id` values silently collapse activities during import; validate uniqueness before generating the file.
4. **Time limits are not quality guarantees.** Timefold's `withTerminationSpentLimit` and FET's `--timelimitseconds` both return the best solution found so far. Always check the hard score is zero before publishing a timetable, never assume "it ran without errors" means "it is feasible".
5. **Semester rollover is the real test.** Whichever tool you pick, run a full dry run on last semester's real data before committing to it. All three will happily produce a beautiful, invalid timetable.

For related scheduling reading, see our [constraint programming solver comparison](../2026-06-22-constraint-programming-solvers-ortools-gecode-choco-minizinc-chuffed/) if you plan to hand-roll the model, and the [school management system guide](../2026-05-02-gibbon-vs-rosariosis-vs-opensis-self-hosted-school-management-guide/) for the surrounding student data. If your problem is closer to queueing than timetabling, the [discrete event simulation frameworks review](../2026-09-25-discrete-event-simulation-frameworks-simpy-salabim-jaamsim-omnetpp/) covers that ground.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "UniTime vs Timefold vs FET in 2026: Which Open-Source Timetabling Engine Actually Fits Your Institution?",
  "description": "Hands-on comparison of UniTime, Timefold Solver and FET for open-source timetabling, with real Docker configs, solver code and deployment pitfalls.",
  "datePublished": "2026-11-12",
  "dateModified": "2026-11-12",
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

### Is UniTime really free for a whole university?

Yes. UniTime is Apache-2.0 licensed under the Apereo Foundation, with no per-student fee. Your real costs are infrastructure (a MySQL instance and a Tomcat container) and the staff time to configure rooms, curricula and constraints. Institutions typically spend two to six weeks on initial configuration before the first real semester.

### Can FET handle a university-sized problem?

Usually not comfortably. FET is designed for school-level problems — a few hundred activities. Beyond roughly 1,000 activities, generation times grow sharply and you end up manually relaxing constraints. For university scale, UniTime or a Timefold-based service is the better fit.

### Do I need to know Java to use Timefold?

Yes, for anything beyond the sample projects. Timefold's model is Java/Kotlin classes with annotations, and constraints are code. If your team is Python-only, either wrap a solver service in Java or look at constraint programming tools with Python bindings instead.

### Which one produces the most optimised timetable?

Timefold, by a wide margin, because you can weight and tune every soft constraint and give the solver real CPU time. UniTime's optimiser is good but its objective is fixed by the platform's design. FET is a fast feasibility generator, not an optimiser.

### Can I run timetabling in a container with no GUI at all?

Yes for all three, with different mechanisms: UniTime is a web application by design, Timefold runs inside your own service (often a Quarkus or Spring Boot container), and FET exposes `fet-cl` for headless generation from an XML file.

### How do I move data between them?

Realistically you do not. UniTime stores everything in MySQL, Timefold keeps the model in your application, and FET uses XML. Practical migration means exporting to CSV and rebuilding the model — plan a parallel run for one semester rather than a cutover.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
