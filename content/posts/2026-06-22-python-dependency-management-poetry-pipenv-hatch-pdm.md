---
title: "Self-Hosted Python Dependency Management: Poetry vs Pipenv vs Hatch vs PDM"
date: "2026-06-22"
tags: ["python", "dependency-management", "packaging", "developer-tools", "pip", "virtualenv"]
draft: false
---

Python's packaging ecosystem has evolved dramatically over the past decade. From the early days of `setup.py` and `requirements.txt`, the community has converged on a new generation of dependency and project management tools that handle virtual environments, lock files, build systems, and publishing in a unified workflow. This guide compares the four leading tools — **Poetry**, **Pipenv**, **Hatch**, and **PDM** — examining their approach to dependency resolution, lock file formats, PEP compliance, and real-world development ergonomics.

## Comparison: Poetry vs Pipenv vs Hatch vs PDM

Each tool approaches the same core problem — managing Python project dependencies and environments — with a different philosophy. Poetry emphasizes a holistic project management experience. Pipenv was the first to popularize `Pipfile` and `Pipfile.lock`. Hatch focuses on the build and publishing workflow. PDM champions the latest Python packaging standards (PEP 621).

| Feature | Poetry | Pipenv | Hatch | PDM |
|---------|--------|--------|-------|-----|
| **Stars** | 34,292 | 25,062 | 7,182 | 8,642 |
| **Lock File** | `poetry.lock` | `Pipfile.lock` | `hatch.lock` (via uv) | `pdm.lock` |
| **Build Backend** | Poetry Core | setuptools + pipenv | Hatchling | pdm-backend |
| **PEP 621 (pyproject.toml)** | Partial (proprietary section) | No | Fully compliant | Fully compliant |
| **Dependency Resolution** | SAT solver | pip resolver | Delegates to pip/uv | Resolution algorithm |
| **Virtual Env Management** | Built-in (venv) | Built-in (virtualenv) | Delegates to uv/pip | Built-in (venv) |
| **Plugin System** | Yes | No | Yes (hatch plugins) | Yes |
| **Publish to PyPI** | Built-in | No | Built-in (hatch publish) | Built-in |
| **Script/Task Runner** | Basic (poetry run) | pipenv scripts | Hatch scripts (env matrices) | pdm run + scripts |
| **Last Updated** | June 2026 | June 2026 | June 2026 | June 2026 |

## Poetry: The Holistic Project Manager

Poetry, created by Sébastien Eustace, was the first tool to offer a unified `pyproject.toml`-based workflow: dependency management, virtual environments, building, and publishing in a single CLI. Its SAT-based dependency resolver was a significant improvement over pip's original backtracking resolver.

**Installation:**

```bash
curl -sSL https://install.python-poetry.org | python3 -
# Or via pipx (recommended)
pipx install poetry
```

**Creating a New Project:**

```bash
poetry new my-project
cd my-project

# Add dependencies
poetry add requests httpx
poetry add --group dev pytest black ruff

# Install all dependencies (creates venv automatically)
poetry install

# Run commands inside the venv
poetry run python main.py

# Build and publish
poetry build
poetry publish
```

**pyproject.toml (Poetry section):**

```toml
[tool.poetry]
name = "my-project"
version = "0.1.0"
description = "A sample Python project"
authors = ["Your Name <you@example.com>"]

[tool.poetry.dependencies]
python = "^3.10"
requests = "^2.31"
httpx = "^0.27"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
ruff = "^0.5"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

Poetry uses its own `[tool.poetry]` section in `pyproject.toml` rather than the PEP 621 standard `[project]` table. This is its primary criticism — it predates PEP 621 and has been slow to adopt it. The Poetry team has indicated PEP 621 support is planned for Poetry 2.0.

**Strengths:** Mature ecosystem, excellent dependency resolution, deeply integrated workflow, large community.

**Weaknesses:** Non-standard `pyproject.toml` section, heavier than alternatives, slower resolution on very large dependency trees.

## Pipenv: The Pioneer

Pipenv, created by Kenneth Reitz and now maintained by the Python Packaging Authority (PyPA), was the first tool to popularize deterministic builds with `Pipfile` and `Pipfile.lock`. It was once the "officially recommended" packaging tool, though this endorsement has since been walked back.

**Installation:**

```bash
pip install --user pipenv
# Or via pipx
pipx install pipenv
```

**Workflow:**

```bash
cd my-project/

# Initialize Pipfile and install dependencies
pipenv install requests httpx
pipenv install --dev pytest black ruff

# Activate the virtual environment shell
pipenv shell

# Or run commands without activating
pipenv run python main.py

# Generate lock file
pipenv lock
```

**Pipfile:**

```toml
[[source]]
url = "https://pypi.org/simple"
verify_ssl = true
name = "pypi"

[packages]
requests = "*"
httpx = "*"

[dev-packages]
pytest = "*"
black = "*"
ruff = "*"

[requires]
python_version = "3.10"
```

Pipenv's key innovation was the `Pipfile.lock`, which pins exact versions and hashes for reproducibility. However, its dependency resolution was notoriously slow before the 2020 pip resolver rewrite, and it has lost mindshare to Poetry and PDM.

**Strengths:** Simple concept, `Pipfile.lock` for deterministic builds, PyPA affiliation, good for existing pip users.

**Weaknesses:** Slower adoption of new standards, no built-in build/publish workflow, limited script management, community momentum has shifted.

## Hatch: The Build and Matrix Specialist

Hatch, created by Ofek Lev and now a PyPA project, takes a different approach: it focuses on build backends (via Hatchling), environment matrices, and version management, while delegating dependency installation to pip or uv. Hatch is particularly strong for library authors who need to test across multiple Python versions.

**Installation:**

```bash
pipx install hatch
```

**Workflow:**

```bash
hatch new my-project
cd my-project

# Create environments for different Python versions
hatch env create py310
hatch env create py312

# Run tests across all environments
hatch run test

# Build the project
hatch build

# Publish to PyPI
hatch publish
```

**pyproject.toml (Hatch/PEP 621):**

```toml
[project]
name = "my-project"
version = "0.1.0"
description = "A sample Python project"
requires-python = ">=3.10"
dependencies = [
    "requests>=2.31",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "ruff>=0.5",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.envs.default]
features = ["dev"]

[[tool.hatch.envs.matrix]]
python = ["3.10", "3.11", "3.12", "3.13"]
```

Hatch uses environment matrices to run commands across multiple Python versions with a single command — `hatch run test` runs pytest in every matrix environment. This is invaluable for library maintainers who support multiple Python versions. Hatch delegates the actual installation to pip or uv, making it faster than Poetry for pure dependency operations.

**Strengths:** PEP 621 compliant, excellent multi-environment testing, fast (delegates to uv), good for library authors, Hatchling build backend is performant.

**Weaknesses:** Less integrated than Poetry for application development, no built-in dependency resolver (delegates), younger ecosystem.

## PDM: The Standards Champion

PDM (Python Development Master) is the newest and most standards-compliant tool in this comparison. It was the first to fully adopt PEP 621 (`[project]` table in `pyproject.toml`) and PEP 582 (local `__pypackages__` directory, though later deprecated). PDM prioritizes speed, correctness, and compliance with the latest Python packaging standards.

**Installation:**

```bash
curl -sSL https://pdm-project.org/install-pdm.py | python3 -
# Or via pipx
pipx install pdm
```

**Workflow:**

```bash
pdm init my-project
cd my-project

# Add dependencies (automatically creates venv)
pdm add requests httpx
pdm add --dev pytest ruff

# Run commands
pdm run python main.py

# Build
pdm build

# Publish
pdm publish
```

**pyproject.toml (PDM/PEP 621):**

```toml
[project]
name = "my-project"
version = "0.1.0"
description = "A sample Python project"
requires-python = ">=3.10"
dependencies = [
    "requests>=2.31",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "ruff>=0.5",
]

[build-system]
requires = ["pdm-backend"]
build-backend = "pdm.backend"

[tool.pdm]
distribution = true
```

PDM's lock file format differs from Poetry's — it uses a TOML-based `pdm.lock` that includes metadata groups, making it easier to inspect and version-control. PDM also supports PEP 582 local packages (for environments without virtualenvs), plugin system for custom backends, and script definitions in `pyproject.toml`.

**Strengths:** Full PEP 621 compliance, fast resolution, excellent standards support, plugin ecosystem, strong Chinese community.

**Weaknesses:** Smaller community than Poetry, fewer tutorials and third-party integrations, younger project.

## Migration Guide: Choosing Your Tool

If you're starting a new Python project in 2026, here's a practical decision framework:

- **Choose Poetry** if you want the most mature, well-documented option with the largest community. It's the safe choice for teams that value stability and ecosystem breadth. The non-standard `pyproject.toml` section is a minor concern for applications.

- **Choose PDM** if you care about PEP compliance and want the fastest, most modern tool. PDM is increasingly the choice for new open-source libraries that want to follow Python packaging best practices.

- **Choose Hatch** if you're a library maintainer who needs multi-Python-version testing matrices and a fast, reliable build workflow. Hatch + uv is the fastest combination for dependency installation.

- **Choose Pipenv** only if you're maintaining an existing project that already uses it. For new projects, the other three tools offer better workflows and more active development.

For more on the Python development ecosystem, see our [Python configuration libraries guide](../2026-06-22-python-configuration-libraries-pydantic-dynaconf-decouple-environs-guide/) and [code formatting and linting tools comparison](../2026-06-20-code-linter-formatter-tools-eslint-prettier-ruff-black-rubocop/).

## FAQ

### Can I use two dependency managers in the same project?

Technically yes, but you shouldn't. Each tool maintains its own lock file (`poetry.lock`, `Pipfile.lock`, `pdm.lock`, etc.) and virtual environment. Mixing them leads to inconsistent dependency resolution, conflicting lock files, and confusion about which environment is active. Pick one tool per project and stick with it.

### Does Poetry support PEP 621 yet?

As of June 2026, Poetry does not fully support PEP 621. It uses its own `[tool.poetry]` section in `pyproject.toml`. The Poetry team has indicated PEP 621 support is coming in a future major version, but there is no firm timeline. If PEP 621 compliance is important to your project, use Hatch or PDM instead.

### What's the fastest tool for dependency installation?

Hatch delegating to `uv` is the fastest combination for pure dependency installation. PDM is also fast due to its optimized resolution algorithm. Poetry's SAT solver is thorough but can be slower on large dependency trees with complex constraints. For everyday development, all four tools are fast enough — the differences matter most in CI/CD pipelines with cold caches.

### How do I migrate from `requirements.txt` to Poetry/PDM?

For Poetry: run `poetry init` in your project directory, then use `poetry add` for each dependency. Alternatively, use `poetry add $(cat requirements.txt)` for a bulk import. For PDM: use `pdm import requirements.txt` which automatically parses your requirements file. Both tools will resolve and pin versions in their respective lock files.

### Which tool is best for monorepos with multiple Python packages?

PDM and Hatch both handle monorepos well through their workspace/plugin systems. PDM supports backend plugins that can manage monorepo layouts. Hatch's environment matrices work across multiple packages within a single repository. Poetry has limited monorepo support through its plugin system and path dependencies, but it's not its primary strength.

### Can I use these tools inside Docker containers?

Yes. All four tools work well in Docker. The recommended pattern is to use multi-stage builds: copy `pyproject.toml` and lock file first, install dependencies, then copy source code. A typical Dockerfile pattern:

```dockerfile
FROM python:3.12-slim
RUN pip install poetry
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && poetry install --no-root --only main
COPY . .
CMD ["python", "main.py"]
```

Set `virtualenvs.create false` to install into the system Python rather than a virtual environment — the Docker container is already isolated.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Python Dependency Management: Poetry vs Pipenv vs Hatch vs PDM",
  "description": "In-depth comparison of Python dependency management tools — Poetry, Pipenv, Hatch, and PDM — covering PEP 621 compliance, lock file formats, build backends, virtual environment management, and migration guidance.",
  "datePublished": "2026-06-22",
  "dateModified": "2026-06-22",
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
