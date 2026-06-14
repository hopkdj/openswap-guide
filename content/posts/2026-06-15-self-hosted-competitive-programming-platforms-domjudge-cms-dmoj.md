---
title: "Self-Hosted Competitive Programming Platforms: DOMjudge vs CMS vs DMOJ"
date: "2026-06-15"
tags: ["competitive-programming", "coding-contest", "judge-system", "self-hosted", "open-source", "education", "acm-icpc"]
draft: false
---

## Why Self-Host a Programming Contest Platform?

Competitive programming has grown from university computer science departments into a global phenomenon. Platforms like Codeforces, AtCoder, and LeetCode attract millions of participants — but for universities, companies running internal hackathons, and coding bootcamps, self-hosting your own judging platform offers critical advantages.

A self-hosted contest platform gives you full control over problem sets, submission policies, scoring rules, and participant management. You're not dependent on a third-party service's uptime or API limits. For academic institutions running ACM-ICPC regionals or internal selection contests, self-hosting is often mandatory to meet security and fairness requirements.

If you're already running a code execution sandbox for safe evaluation, our [guide to Judge0, Piston, and Runtipi](../self-hosted-code-execution-sandbox-judge0-piston-runtipi-guide-2026/) covers the execution backend these platforms typically integrate with. For broader programming education tools, see our [guide to interactive programming learning platforms](../2026-06-07-self-hosted-interactive-learning-platforms-oppia-kolibri-adapt-guide/).

## Comparison at a Glance

| Feature | DOMjudge | CMS | DMOJ |
|---------|----------|-----|------|
| **GitHub Stars** | 893+ | 1,024+ | 1,171+ |
| **Primary Language** | PHP | Python | Python |
| **License** | GPL-2.0 | AGPL-3.0 | AGPL-3.0 |
| **Docker Support** | ✅ docker-compose | Manual setup | Manual setup |
| **Contest Format** | ICPC-style | IOI-style | Both |
| **Web Interface** | ✅ Bootstrap UI | ✅ Web UI | ✅ Modern UI |
| **Judge System** | Built-in (judgedaemon) | Built-in (EvaluationService) | Built-in (DMOJ Judge) |
| **Multiple Judgers** | ✅ Distributed | ✅ Distributed | ✅ Distributed |
| **API** | REST API | RPC API | REST API |
| **Scoreboard** | ✅ Real-time | ✅ Real-time | ✅ Real-time |
| **Problem Types** | Batch, interactive, output-only | Batch, communication, output-only | Batch, interactive, function |
| **Languages** | C, C++, Java, Python, Kotlin, +more | C, C++, Pascal, +extensible | C, C++, Java, Python, 60+ via executors |
| **Auth** | Local + LDAP + IP-restricted | Local | Local + OAuth |
| **Last Update** | June 2026 | June 2026 | June 2026 |

## DOMjudge: The ICPC Standard

DOMjudge is the official judging system used by the ACM International Collegiate Programming Contest (ICPC) World Finals. It's battle-tested at the highest levels of competitive programming, handling thousands of teams across multiple sites simultaneously.

**Key Strengths:**
- Official ICPC World Finals system — proven at scale
- Distributed judging architecture for horizontal scaling
- Balloon/print delivery system for on-site events
- Shadow mode for testing before live contests
- Comprehensive jury interface for problem management

**Docker Compose Deployment:**

```yaml
version: "3.8"
services:
  domserver:
    image: domjudge/domserver:latest
    container_name: domjudge-domserver
    ports:
      - "8080:80"
    environment:
      - MYSQL_HOST=mariadb
      - MYSQL_USER=domjudge
      - MYSQL_PASSWORD=domjudge_password
      - MYSQL_DATABASE=domjudge
      - MYSQL_ROOT_PASSWORD=root_password
      - FPM_MAX_CHILDREN=40
    volumes:
      - ./domserver:/opt/domjudge/domserver
    depends_on:
      - mariadb
    restart: unless-stopped

  mariadb:
    image: mariadb:11
    container_name: domjudge-db
    environment:
      - MYSQL_ROOT_PASSWORD=root_password
      - MYSQL_USER=domjudge
      - MYSQL_PASSWORD=domjudge_password
      - MYSQL_DATABASE=domjudge
    volumes:
      - ./mariadb:/var/lib/mysql
    restart: unless-stopped
    command: --max-connections=1000 --max-allowed-packet=256M

  judgehost:
    image: domjudge/judgehost:latest
    container_name: domjudge-judgehost
    privileged: true
    environment:
      - DOMSERVER_BASEURL=http://domserver/
      - JUDGEDAEMON_USERNAME=judgehost
      - JUDGEDAEMON_PASSWORD=judgehost_password
    depends_on:
      - domserver
    restart: unless-stopped
```

## CMS: The IOI System

CMS (Contest Management System) is the platform developed for and used by the International Olympiad in Informatics (IOI). It's designed for the IOI-style contest format where participants submit solutions and receive feedback during the competition.

**Key Strengths:**
- Official IOI competition platform
- Supports communication tasks and output-only problems
- Sophisticated scoring with subtask support
- Built-in ranking and medal calculation
- AWS integration for cloud-based contest infrastructure

**Installation:**

```bash
# Clone the repository
git clone https://github.com/cms-dev/cms.git
cd cms

# Install dependencies (Ubuntu/Debian)
sudo apt-get install build-essential python3-dev python3-pip     postgresql postgresql-client libpq-dev     libcgi-session-perl libwww-perl libcgi-fast-perl

# Install CMS
pip3 install -r requirements.txt
python3 setup.py install

# Initialize database
cmsInitDB

# Start services
cmsResourceService -a ALL
cmsLogService
cmsScoringService
cmsChecker
cmsEvaluationService
cmsRankingWebServer
```

## DMOJ: Modern Online Judge

DMOJ (Don Mills Online Judge) is a modern, feature-rich online judge platform that powers the popular dmoj.ca website. It supports both continuous judging (like Codeforces/AtCoder) and contest modes, making it the most versatile of the three platforms.

**Key Strengths:**
- Most modern UI of the three platforms
- Supports 60+ programming languages
- Built-in problem suggestion and voting system
- Organization and user point tracking
- Blog and communication features for community building

**Installation:**

```bash
# Clone the repository
git clone https://github.com/DMOJ/site.git
cd site

# Install Python dependencies
pip3 install -r requirements.txt

# Install frontend dependencies
npm install
npm run build

# Configure settings
cp dmoj/local_settings.py.example dmoj/local_settings.py
# Edit local_settings.py with your database credentials

# Initialize database
python3 manage.py migrate
python3 manage.py loaddata navbar
python3 manage.py loaddata language_small

# Create superuser
python3 manage.py createsuperuser

# Start the server
python3 manage.py runserver 0.0.0.0:8000
```

## Setting Up a Judge Server

All three platforms use a separate judge process that compiles and executes submissions in a sandbox. For production, you'll want to run judge servers on dedicated machines:

```bash
# DOMjudge judgehost setup
docker run -d --privileged \
  -e DOMSERVER_BASEURL=http://domserver/ \
  -e JUDGEDAEMON_USERNAME=judgehost \
  -e JUDGEDAEMON_PASSWORD=yourpassword \
  domjudge/judgehost:latest

# DMOJ judge setup
git clone https://github.com/DMOJ/judge.git
cd judge
pip3 install -e .
dmoj-judge -c judge.yml
```

For security, judge servers should run on isolated machines or containers with appropriate resource limits. Our [container sandboxing guide](../2026-04-20-gvisor-vs-kata-containers-vs-firecracker-container-sandboxing-guide-2026/) covers additional isolation options.

## Choosing the Right Platform

- **Choose DOMjudge** if you're running ACM-ICPC style contests with strict time limits, balloon delivery, and multiple-site support. It's the most battle-tested option.

- **Choose CMS** if you're running IOI-style competitions with subtask scoring, communication problems, or need official IOI compatibility.

- **Choose DMOJ** if you want a modern community platform with continuous judging, 60+ language support, and the flexibility to run both contest and practice modes.

## Security Hardening for Judge Systems

Running untrusted code is inherently dangerous — a contest participant could submit malicious code that attempts to escape the sandbox. All three platforms implement defense in depth:

**Filesystem Isolation**: Judge processes should run with minimal filesystem access. DOMjudge's judgehost uses chroot environments; DMOJ's judge uses Linux namespaces. Never mount host filesystem paths into the judge container.

**Resource Limits**: Configure strict CPU time, memory, and process limits per submission. DOMjudge enforces these via cgroups — typical limits are 2 seconds CPU, 256MB RAM per submission. DMOJ supports per-language limits since Python and Java have different baseline memory footprints.

**Network Restrictions**: Judge servers should have no outbound internet access. All three platforms operate with the judge server firewalled — submissions can only read/write to the problem's working directory.

**Compiler Sandboxing**: The judge compiles submissions before execution. Limit compilation time (typically 30 seconds) and block compiler flags that could enable unsafe operations (-static, -fpic for certain exploits).

**Monitoring**: Set up alerts for abnormal judge behavior — spikes in CPU usage, unexpected process trees, or network activity from the judge machine. Integration with a HIDS like Wazuh or OSSEC adds an additional security layer.


## FAQ

### Can these platforms handle thousands of simultaneous participants?

Yes. DOMjudge runs the ICPC World Finals with hundreds of teams and thousands of submissions. Both DOMjudge and DMOJ support distributed judging where multiple judge servers process submissions in parallel. CMS has been used at IOI with 300+ contestants across multiple days.

### How do I prevent malicious code from damaging the judge server?

All three platforms run submissions in sandboxed environments. DOMjudge and DMOJ use Linux cgroups and seccomp filters. For production, run judge servers on isolated VMs or containers separate from your web server. Never run the judge process on the same machine as your database.

### Can I use these for corporate coding interviews?

Yes. While designed for competitive programming, these platforms work well for technical screening. DMOJ's 60+ language support is ideal for companies with diverse tech stacks. Configure a private contest with your interview problems and time limits.

### What's the difference between ICPC and IOI contest formats?

ICPC (DOMjudge) uses a penalty-based scoring system where incorrect submissions add time penalties. IOI (CMS) uses subtask-based scoring where partial solutions earn partial points. DMOJ supports both formats.

### How do these compare to HackerRank or Codility?

HackerRank and Codility are SaaS platforms with per-candidate pricing. Self-hosted alternatives eliminate per-user costs — critical for universities running weekly contests with hundreds of students. For code execution sandboxing specifically, our [Judge0 comparison](../self-hosted-code-execution-sandbox-judge0-piston-runtipi-guide-2026/) covers the execution backend these platforms depend on.

### What hardware do I need for a contest with 100 participants?

A single judge server with 4 CPU cores and 8GB RAM can handle a 100-participant contest comfortably. For larger events, add additional judge servers. The web server (DOMserver/CMS/DMOJ) is lightweight — a 2GB VPS is sufficient.

---

<section>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Competitive Programming Platforms: DOMjudge vs CMS vs DMOJ",
  "description": "Comprehensive comparison of open-source self-hosted competitive programming judging platforms. Compare DOMjudge (ICPC official), CMS (IOI official), and DMOJ (modern online judge) — deployment guides with Docker Compose, distributed judging setup, and contest format analysis.",
  "datePublished": "2026-06-15",
  "dateModified": "2026-06-15",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
