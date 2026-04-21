---
title: "Best Self-Hosted Terminal Recording & Screencast Tools 2026: asciinema vs vhs vs ttyrec"
date: 2026-04-17
tags: ["comparison", "guide", "self-hosted", "developer-tools"]
draft: false
description: "Compare asciinema, vhs, and ttyrec — the best open-source tools for recording terminal sessions, creating tutorial GIFs, and documenting CLI workflows in 2026."
---

Recording terminal sessions is an essential skill for developers, educators, and DevOps engineers. Whether you're creating a tutorial for your team, documenting a deployment procedure, building a demo for a conference talk, or keeping an audit trail of production changes — having a reliable way to capture and replay terminal output is invaluable.

Commercial screen recorders work, but they produce heavy video files, expose your entire desktop, and strip away the text-based nature of terminal content. Dedicated terminal recording tools produce lightweight, searchable, text-based recordings that can be embedded in documentation, shared as interactive players, or converted to GIFs and videos.

In this guide, we compare the three leading open-source terminal recording tools: **asciinema**, **vhs** (by Charm), and **ttyrec**. Each serves a different workflow, and understanding their strengths will help you pick the right tool.

## Why Self-Host Terminal Recording

Cloud-based terminal recording services are convenient, but self-hosting offers important advantages:

- **Full privacy**: Terminal recordings often contain sensitive data — file paths, configuration values, server names, and sometimes credentials. Self-hosting ensures this content never leaves your infrastructure.
- **Offline availability**: Recordings are stored locally and accessible without an internet connection, which matters for teams in restricted environments or with unreliable connectivity.
- **No rate limits or quotas**: Free tiers on hosted platforms limit recording length, storage, or views. Self-hosted tools have no artificial limits.
- **Custom branding and integration**: Self-hosted players can be embedded in your own documentation site with your branding, styling, and access controls.
- **Long-term archival**: When a cloud service shuts down or changes pricing, your recordings are at risk. Self-hosted recordings are plain text files that will outlive any platform.

## asciinema: The Standard for Terminal Recording

**asciinema** is the most widely adopted terminal recording tool. It records terminal sessions as plain-text cast files that capture every character, timing, and terminal escape sequence. Recordings can be played back in a terminal, embedded as an interactive player on websites, or uploaded to the public asciinema.org service.

### How It Works

asciinema attaches to your shell's pseudo-terminal and records everything that gets printed — text, colors, cursor movements — along with precise timing information. The output is a JSON-formatted `.cast` file that contains header metadata followed by timestamped events.

### Installation

On Debian/Ubuntu:

```bash
sudo apt update
sudo apt install asciinema
```

On macOS with Homebrew:

```bash
brew install asciinema
```

From PyPI (works everywhere with Python 3):

```bash
pip install asciinema
```

### Recording Your First Session

```bash
asciinema rec deployment.cast
```

You now have a live terminal where everything you type and every output line is recorded. When finished, press `Ctrl+D` or type `exit`. The file `deployment.cast` is saved to your working directory.

Play it back:

```bash
asciinema play deployment.cast
```

Share it on asciinema.org (optional):

```bash
asciinema auth          # Link to your account
asciinema upload deployment.cast
```

### Self-Hosting the asciinema Server

For complete privacy, run your own asciinema server:

```yaml
version: "3.8"
services:
  asciinema:
    image: asciinema/asciinema-server:latest
    ports:
      - "4000:4000"
    environment:
      - DATABASE_URL=ecto://postgres:postgres@db/asciinema
      - SECRET_KEY_BASE=$(openssl rand -hex 32)
      - HOST_URL=https://asciinema.yourdomain.com
      - REGISTRATION_ENABLED=true
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:16
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=asciinema
    volumes:
      - pgdata:/var/lib/[postgresql](https://www.postgresql.org/)/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 3s
      retries: 5
    restart: unless-stopped

volumes:
  pgdata:
```

Configure your local asciinema client to use your server by editing `~/.config/asciinema/config`:

```ini
[api]
url = https://asciinema.yourdomain.com
```

Then upload as usual — recordings go to your server instead of the public instance.

### Embedding Recordings

Once uploaded, embed the player in any HTML page:

```html
<script id="asciicast-12345"
        src="https://asciinema.yourdomain.com/a/12345.js"
        async>
</script>
```

Or embed as an iframe for more control:

```html
<iframe src="https://asciinema.yourdomain.com/a/12345/embed"
        width="800"
        height="500"
        frameborder="0"
        allowfullscreen>
</iframe>
```

For static sites like Hugo, include the embed script directly in your Markdown:

```markdown
<script id="asciicast-demo"
        src="/recordings/deployment.js"
        async></script>
```

### Converting to GIF and Video

The `agg` (asciinema gif generator) tool converts `.cast` files to animated GIFs:

```bash
# Install agg (Rust-based)
cargo install agg

# Convert with custom styling
agg \
  --font-size 14 \
  --font-family "JetBrains Mono" \
  --theme solarized-dark \
  --title "Deploying to Production" \
  deployment.cast \
  deployment.gif
```

For MP4 video output, pipe through `ffmpeg`:

```bash
agg --theme solarized-dark deployment.cast - | \
  ffmpeg -i - -c:v libx264 -pix_fmt yuv420p deployment.mp4
```

### Advanced Usage

Record with metadata and a custom prompt:

```bash
asciinema rec \
  --command "bash --norc --noprofile" \
  --title "[kubernetes](https://kubernetes.io/) Debugging Session" \
  --idle-time-limit 2 \
  --env "TERM,SHELL,USER" \
  k8s-debug.cast
```

Key flags:

| Flag | Purpose |
|------|---------|
| `--command` | Override the default shell |
| `--title` | Recording title for metadata |
| `--idle-time-limit` | Cap idle gaps (seconds) to speed up playback |
| `--env` | Comma-separated env vars to include in header |
| `--append` | Append to an existing recording |
| `--raw` | Record raw stdin/stdout (no terminal emulation) |

### Pros and Cons

| Strengths | Weaknesses |
|-----------|------------|
| Industry standard — widest tool ecosystem | Upload requires network access (unless self-hosted) |
| Plain-text `.cast` format is human-readable | Player is JavaScript-dependent for web embeds |
| Rich metadata in header (env, terminal size, theme) | No built-in editing — cannot trim or splice recordings |
| Excellent web player with speed control and copy-paste | GIF conversion requires a separate tool (agg) |
| Works across Linux, macOS, and Windows (WSL) | No audio recording — terminal only |

## vhs: Terminal Recording as Code

**vhs** (Video Helper System) by Charm is a fundamentally different approach: instead of recording live sessions, you write a "tape" script that describes the terminal actions, and vhs renders it to GIF, MP4, or WebM. It's like a screenplay for your terminal.

### How It Works

You write a `.tape` file with instructions — type this command, wait for output, press enter, clear the screen — and vhs executes it in a headless terminal, capturing the result as a high-quality animation. This gives you pixel-perfect, repeatable recordings with no typos or accidental keypresses.

### Installation

On Debian/Ubuntu (from .deb):

```bash
VHS_VERSION="0.9.0"
curl -Lo /tmp/vhs.deb "https://github.com/charmbracelet/vhs/releases/download/v${VHS_VERSION}/vhs_${VHS_VERSION}_linux_amd64.deb"
sudo apt install /tmp/vhs.deb
```

On macOS with Homebrew:

```bash
brew install vhs
```

From Go:

```bash
go install github.com/charmbracelet/vhs@latest
```

### Writing Your First Tape

Create `deploy.tape`:

```
# Setup the terminal
Output deploy.gif
Width 800
Height 500
Set FontSize 16
Set Padding 20
Set Theme "Catppuccin Mocha"

# Run the commands
Hide
Type "ssh deploy@production" Enter
Sleep 500ms
Show

Type "cd /opt/app" Enter
Sleep 300ms

Type "git pull origin main" Enter
Sleep 2s

Type "[docker](https://www.docker.com/) compose up -d" Enter
Sleep 3s

Type "docker compose logs --tail 20" Enter
Sleep 1s
```

Render it:

```bash
vhs deploy.tape
```

This produces `deploy.gif` — a clean, professional terminal animation with no mistakes.

### Tape File Syntax

The tape language supports a rich set of commands:

```
# Output configuration
Output demo.gif
Output demo.mp4
Output demo.webm
Output demo.png          # Single frame screenshot

# Terminal appearance
Width 900
Height 600
Set FontSize 14
Set FontFamily "Fira Code"
Set Padding 30
Set MarginFill "#1a1b26"
Set Theme "Tokyo Night"
Set BorderRadius 10

# Typing control
Type "kubectl get pods" Enter
Type --hide "export SECRET=xxx" Enter
Sleep 1s
Sleep 500ms

# Window management
Screenshot frame.png
Show
Hide

# Loop and conditions (basic)
Type "for i in 1 2 3; do echo \$i; done" Enter
Sleep 1s
```

### Recording from a Live Session

vhs also supports recording live sessions (similar to asciinema) with the `record` subcommand:

```bash
vhs record live-session.tape
```

This captures your typing and converts it to a tape file you can edit and re-render.

### CI/CD Integration

vhs shines in CI pipelines because recordings are deterministic and version-controlled:

```yaml
# .github/workflows/recordings.yml
name: Generate Terminal Recordings
on:
  push:
    paths: ["tapes/**/*.tape"]

jobs:
  render:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install vhs
        run: |
          VHS_VERSION="0.9.0"
          curl -Lo /tmp/vhs.deb "https://github.com/charmbracelet/vhs/releases/download/v${VHS_VERSION}/vhs_${VHS_VERSION}_linux_amd64.deb"
          sudo apt install /tmp/vhs.deb

      - name: Render all tapes
        run: |
          for tape in tapes/*.tape; do
            vhs "$tape"
          done

      - name: Commit GIFs
        run: |
          git config user.name "vhs-bot"
          git config user.email "bot@example.com"
          git add assets/*.gif
          git commit -m "Update terminal recordings" || true
          git push
```

### Docker Deployment for Rendering

Run vhs in a container for consistent rendering across environments:

```yaml
version: "3.8"
services:
  vhs-renderer:
    image: ghcr.io/charmbracelet/vhs:latest
    working_dir: /tapes
    volumes:
      - ./tapes:/tapes
      - ./output:/output
    command: >
      sh -c "
        for tape in *.tape; do
          vhs --output-dir /output \"\$tape\"
        done
      "
```

### Self-Hosting a vhs Web API

For teams that want to render tapes via an API, wrap vhs in a lightweight HTTP service:

```python
# vhs_api.py — Flask wrapper around vhs
import subprocess
import os
import uuid
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)
TAPE_DIR = "/tmp/vhs-tapes"
OUTPUT_DIR = "/tmp/vhs-output"
os.makedirs(TAPE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.route("/render", methods=["POST"])
def render():
    tape_content = request.json.get("tape", "")
    if not tape_content:
        return jsonify({"error": "No tape content provided"}), 400

    tape_id = str(uuid.uuid4())
    tape_path = os.path.join(TAPE_DIR, f"{tape_id}.tape")
    output_path = os.path.join(OUTPUT_DIR, f"{tape_id}.gif")

    with open(tape_path, "w") as f:
        f.write(tape_content)

    result = subprocess.run(
        ["vhs", "--output", output_path, tape_path],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        return jsonify({"error": result.stderr}), 500

    return send_file(output_path, mimetype="image/gif")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
```

Run it:

```bash
pip install flask
python vhs_api.py
```

Send a tape for rendering:

```bash
curl -X POST http://localhost:8080/render \
  -H "Content-Type: application/json" \
  -d '{"tape": "Output test.gif\nType \"echo hello\" Enter\nSleep 500ms"}' \
  --output test.gif
```

### Pros and Cons

| Strengths | Weaknesses |
|-----------|------------|
| Deterministic — same tape always produces identical output | Not for live recording workflows |
| Version-controlled recordings — tapes are plain text | Requires writing scripts instead of just hitting record |
| Beautiful output — Charm's themes are production-quality | Heavier dependencies (needs a TTY environment) |
| CI/CD friendly — render on every commit | Less flexible for spontaneous recording |
| Multiple output formats (GIF, MP4, WebM, PNG) | No interactive web player for `.cast`-style playback |
| No typos — edit the tape before rendering | Smaller ecosystem than asciinema |

## ttyrec: The Minimalist Terminal Recorder

**ttyrec** is the original Unix terminal recording tool, dating back decades. It's a tiny C program that records raw terminal I/O to a file. No JSON, no metadata, no web players — just bytes.

### How It Works

ttyrec wraps a shell session and records the raw terminal output stream to a file. The format is a simple binary structure: each event is a timestamp followed by the raw data bytes. It's the most lightweight option but requires additional tools for playback and conversion.

### Installation

On Debian/Ubuntu:

```bash
sudo apt install ttyrec
```

From source:

```bash
wget https://files.dyne.org/ttyrec/ttyrec-1.0.tar.gz
tar xzf ttyrec-1.0.tar.gz
cd ttyrec-1.0
./configure
make
sudo make install
```

### Basic Usage

Record a session:

```bash
ttyrec session.log
```

Everything you type and see is recorded to `session.log`. Press `Ctrl+D` to stop.

Play it back at normal speed:

```bash
ttyplay session.log
```

Play at 2x speed:

```bash
ttyplay -s 2 session.log
```

Play with a custom speed function (e.g., skip idle time):

```bash
ttyplay -f my_speed_function.pl session.log
```

### Converting to Text

Extract plain text from a ttyrec recording:

```bash
ttyplay -p /bin/cat session.log > session.txt
```

Convert to asciinema format:

```bash
# Using the tty2asciinema converter
pip install tty2asciinema
tty2asciinema session.log > session.cast
```

### Docker Usage

```yaml
version: "3.8"
services:
  recorder:
    image: alpine:latest
    volumes:
      - ./recordings:/recordings
    command: >
      sh -c "
        apk add ttyrec bash &&
        ttyrec -a /recordings/session.log bash
      "
    stdin_open: true
    tty: true
```

### Pros and Cons

| Strengths | Weaknesses |
|-----------|------------|
| Smallest footprint — tiny binary, zero dependencies | Raw binary format — not human-readable |
| Works on any Unix system | No built-in web player |
| Battle-tested — used for decades in production | No metadata (no terminal size, env, or title) |
| Extremely low overhead during recording | Playback tools are basic |
| Ideal for audit logging and compliance | Requires conversion for modern sharing |

## Feature Comparison

| Feature | asciinema | vhs | ttyrec |
|---------|-----------|-----|--------|
| **Recording mode** | Live session | Scripted (tape) | Live session |
| **Output format** | JSON `.cast` | GIF/MP4/WebM/PNG | Binary log |
| **File size** | Small (text) | Medium (media) | Smallest (binary) |
| **Human-readable** | Yes | Partially (tape) | No |
| **Web player** | Built-in | No | No |
| **Editing support** | No (trim with external tools) | Yes (edit tape) | No |
| **Deterministic** | No (live typing) | Yes (scripted) | No (live typing) |
| **CI/CD friendly** | Moderate | Excellent | Low |
| **Self-hostable server** | Yes (asciinema-server) | Via API wrapper | N/A |
| **Audio** | No | No | No |
| **Color support** | Full ANSI | Full ANSI | Full ANSI |
| **Idle time control** | `--idle-time-limit` | `Sleep` commands | Via playback speed |
| **Dependencies** | Python 3 | Go runtime | C stdlib only |
| **Learning curve** | Low | Medium | Low |

## Choosing the Right Tool

### Pick asciinema if:
- You want to record live sessions with minimal effort
- You need an interactive web player for documentation
- You want the widest compatibility and ecosystem support
- You need to share recordings as embeddable content
- You prefer a simple `rec` / `play` workflow

### Pick vhs if:
- You need pixel-perfect, typo-free recordings for presentations
- You want version-controlled, reproducible terminal demos
- You're building documentation that renders in CI/CD pipelines
- You value beautiful aesthetics with built-in themes
- You create terminal tutorials that need to be updated frequently

### Pick ttyrec if:
- You need the absolute lightest-weight recording tool
- You're recording for audit logs or compliance purposes
- You work on minimal systems where installing Python or Go is impractical
- You want to pipe recordings into custom processing pipelines
- You need maximum compatibility with legacy Unix systems

## Practical Workflows

### Documenting a Deployment Procedure

```bash
# 1. Record the deployment
asciinema rec --title "Production Deploy v2.4" deploy.cast

# 2. Edit idle time (trim long waits)
asciinema cat deploy.cast | \
  python3 -c "
import sys, json
header = json.loads(sys.stdin.readline())
events = [json.loads(line) for line in sys.stdin]
# Cap idle gaps at 2 seconds
result = []
last = 0
for delay, type_, data in events:
    gap = min(delay - last, 2.0)
    result.append([gap, type_, data])
    last = delay
print(json.dumps(header))
for e in result:
    print(json.dumps(e))
" > deploy-edited.cast

# 3. Convert to GIF for the wiki
agg --theme nord --font-size 14 deploy-edited.cast deploy.gif
```

### Creating a Tutorial Series with vhs

```
# intro.tape
Output intro.gif
Width 900
Height 550
Set Theme "Catppuccin Mocha"
Set FontSize 18
Set Padding 25

Hide
Type "Welcome to the Kubernetes tutorial!" Enter
Sleep 800ms
Show

Type "kubectl cluster-info" Enter
Sleep 2s

Type "kubectl get nodes" Enter
Sleep 1.5s

Type "# Let's deploy our first application" Enter
Sleep 1s
```

Render all tutorials in one command:

```bash
for tape in tutorials/*.tape; do
  vhs "$tape"
done
```

### Audit Logging with ttyrec

```bash
# Record all admin sessions (add to /etc/profile)
if [ "$(id -u)" -eq 0 ]; then
  mkdir -p /var/log/ttyrec/$(date +%Y-%m-%d)
  exec ttyrec /var/log/ttyrec/$(date +%Y-%m-%d)/$(whoami)-$$.log
fi
```

Review yesterday's root sessions:

```bash
for log in /var/log/ttyrec/$(date -d yesterday +%Y-%m-%d)/root-*.log; do
  echo "=== $(basename $log) ==="
  ttyplay "$log"
done
```

## Security Considerations

Terminal recordings are sensitive data. Follow these practices:

1. **Sanitize before sharing**: Never share recordings that contain credentials, tokens, or internal hostnames. Use `--hide` in vhs or post-process `.cast` files to redact sensitive output.

2. **Encrypt stored recordings**: If recordings contain production data, encrypt them at rest:

```bash
# Encrypt with age
age -p -o deploy.cast.age deploy.cast

# Decrypt when needed
age -d -o deploy.cast deploy.cast.age
```

3. **Set access controls**: On self-hosted asciinema servers, require authentication and use role-based access:

```bash
# In asciinema-server config
REGISTRATION_ENABLED=false  # No open signups
ADMIN_EMAILS="admin@example.com"
```

4. **Audit what you record**: When using ttyrec for compliance, define retention policies:

```bash
# Delete recordings older than 90 days
find /var/log/ttyrec/ -name "*.log" -mtime +90 -delete
```

5. **Avoid recording interactive prompts**: If a command prompts for a password, the password will be recorded. Use non-interactive flags (`--non-interactive`, `-y`) or environment variables instead.

## Conclusion

Terminal recording tools fill a gap that general-purpose screen recorders cannot: capturing the text-based, interactive nature of the command line in a format that's lightweight, searchable, and easy to share. **asciinema** is the go-to choice for live recording with web playback, **vhs** delivers scripted, pixel-perfect animations ideal for documentation and CI/CD, and **ttyrec** provides the most minimal, dependency-free recording for audit and compliance.

For most development teams, running asciinema with a self-hosted server provides the best balance of ease and control. Teams building public-facing documentation will find vhs's scripted approach produces the most professional results. Organizations with compliance requirements should use ttyrec for its simplicity and low overhead.

All three tools are free, open-source, and can be integrated into your existing workflow. Start recording your terminal sessions today — your future self will thank you when it's time to debug, document, or demo.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
