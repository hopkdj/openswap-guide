---
title: "Self-Hosted Terminal Weather Tools: wttr.in vs wego vs ansiweather — Check Weather Without Apps or APIs"
date: "2026-06-17"
tags: ["weather", "cli-tools", "terminal", "self-hosted", "go", "shell"]
draft: false
---

## Why Check Weather in Your Terminal?

Weather apps have become bloated -- they track your location, serve ads, and consume background resources. Terminal weather tools offer a refreshing alternative: fast, privacy-respecting weather checks that integrate seamlessly into your workflow. You can pipe weather data into status bars, cron jobs, or shell scripts without leaving the command line.

Even better, the most popular terminal weather service -- **wttr.in** -- is fully self-hostable. You can run your own weather service on a $5 VPS and never depend on a third-party API again. In this guide, we compare three leading terminal weather tools: **wttr.in**, **wego**, and **ansiweather**.

## Comparison Table: wttr.in vs wego vs ansiweather

| Feature | wttr.in | wego | ansiweather |
|---------|---------|------|-------------|
| **Stars** | 29,888 | 8,490 | 1,942 |
| **Language** | Go | Go | Shell (POSIX) |
| **Type** | Web service + CLI client | CLI client | CLI client |
| **Self-hostable** | Yes (Docker) | N/A (local only) | N/A (local only) |
| **Weather provider** | Open-Meteo, OpenWeatherMap | OpenWeatherMap, WorldWeatherOnline | OpenWeatherMap |
| **API key required** | No (default) / Optional | Yes | Yes |
| **Forecast support** | 3-day ASCII graph | 5-day table | 5-day text |
| **Location input** | City name, ZIP, coordinates, airport code | City name, coordinates | City name, coordinates |
| **Output formats** | ANSI, PNG, JSON, plain text | ANSI table | ANSI text |
| **Dependencies** | Docker (self-host) or curl (client) | Go binary | Shell + curl + jq |
| **Customization** | URL parameters | Config file | Environment variables |
| **Best for** | Quick curl checks, self-hosting | Rich TUI forecasts | Shell scripts, conky, tmux status |

## wttr.in: The Curl-Based Weather Service

[wttr.in](https://github.com/chubin/wttr.in) is the Swiss Army knife of terminal weather. It's a web service that returns beautifully formatted weather data when you `curl` it -- no API key, no registration, no installation.

### One-Line Weather Check

```bash
# Get weather for your location
curl wttr.in/London

# For a specific location with units
curl "wttr.in/Shanghai?u"

# Airport code
curl wttr.in/JFK

# GPS coordinates
curl wttr.in/37.7749,-122.4194
```

The output is a colorized ANSI terminal display showing current conditions, temperature, wind, humidity, and a 3-day forecast.

### Self-Host wttr.in with Docker

The real power of wttr.in is that you can run your own instance. No more depending on the public service or worrying about rate limits:

```yaml
# docker-compose.yml
version: "3.8"
services:
  wttrin:
    image: ghcr.io/chubin/wttr.in:latest
    container_name: wttrin
    ports:
      - "8080:8080"
    environment:
      - WTTR_MY_LOCATION=Beijing
      - WTTR_DEFAULT_LANGUAGE=zh
    restart: unless-stopped
```

```bash
docker compose up -d
curl http://localhost:8080/Beijing
```

Place it behind a reverse proxy for external access:

```nginx
# nginx reverse proxy config
server {
    listen 443 ssl;
    server_name weather.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

You can also pipe wttr.in output into other tools:

```bash
# Get only the temperature for a script
curl -s "wttr.in/London?format=%t" 
# Output: +15C

# Save weather as PNG for a dashboard
curl -s "wttr.in/London.png" -o weather.png

# JSON output for programmatic use
curl -s "wttr.in/London?format=j1" | jq '.current_condition[0].temp_C'
```

## wego: Rich Terminal Weather Dashboard

[wego](https://github.com/schachmat/wego) takes a different approach -- it's a standalone Go binary that fetches weather data from providers and renders a rich 5-day forecast table directly in your terminal.

### Installation

```bash
# Install via Go
go install github.com/schachmat/wego@latest

# Or download pre-built binary from GitHub releases
wget https://github.com/schachmat/wego/releases/latest/download/wego-linux-amd64
chmod +x wego-linux-amd64
sudo mv wego-linux-amd64 /usr/local/bin/wego
```

### Configuration

Create `~/.wegorc` (or use environment variables):

```ini
# ~/.wegorc
location=Beijing
backend=openweathermap
openweathermap-api-key=YOUR_API_KEY
units=metric
```

Then run:

```bash
wego
# Displays a 5-day table with temperature, precipitation, wind, and weather icons
wego 3       # 3-day forecast
wego London  # Different location
```

wego outputs a colorized ASCII table showing temperature ranges, precipitation probability, wind speed/direction, and weather conditions for each day. The display is information-dense and ideal for quick morning checks.

### Custom Backend Configuration

wego supports multiple weather backends -- useful if one provider is slow or unavailable:

```ini
# Use WorldWeatherOnline with free tier
backend=worldweatheronline
worldweatheronline-api-key=YOUR_WWO_KEY
worldweatheronline-location=Shanghai
```

## ansiweather: Shell-Native Weather for Scripts

[ansiweather](https://github.com/fcambus/ansiweather) is the most lightweight option -- a single POSIX shell script that fetches weather data from OpenWeatherMap and outputs colored ANSI text. At under 500 lines of shell, it's trivially auditable.

### Installation

```bash
# Clone the repo
git clone https://github.com/fcambus/ansiweather.git
cd ansiweather

# Or install via package manager
# macOS: brew install ansiweather
# Arch: yay -S ansiweather
```

### Configuration

```bash
export OPENWEATHERMAP_API_KEY="your_key"
export ANSIWEATHER_LOCATION="Beijing,CN"
export ANSIWEATHER_UNITS="metric"
```

### Basic Usage

```bash
./ansiweather
# Output: Weather in Beijing: 22C and partly cloudy => 18 to 26C

# Five-day forecast
./ansiweather -f 5

# Minimal output for status bars
./ansiweather -F
# Output: 22C SUNNY
```

### Integration Examples

ansiweather excels at embedding weather data into system components:

```bash
# tmux status bar (add to ~/.tmux.conf)
set -g status-right "#(ansiweather -F)"

# Conky desktop widget
${execi 300 ansiweather -l "Beijing,CN" -u metric}

# Shell prompt (add to ~/.bashrc)
export PROMPT_COMMAND='PS1="$(ansiweather -F) \\w $ "'
```

You can also use it in cron jobs for weather-based automation:

```bash
# crontab: Water plants only if it won't rain tomorrow
0 6 * * * ansiweather -f 2 | grep -q "rain" || /usr/local/bin/water-plants.sh
```

## Choosing the Right Weather Tool

| Use Case | Best Tool |
|----------|-----------|
| Quick curl weather check | wttr.in (public) |
| Self-hosted weather service | wttr.in (Docker) |
| Rich 5-day forecast view | wego |
| Shell scripts and automation | ansiweather |
| tmux/conky/status bar integration | ansiweather |
| No API key required | wttr.in |
| JSON/programmatic access | wttr.in |

## Why Self-Host Your Weather Service?

Running your own wttr.in instance gives you complete control over weather data access. No rate limits, no API key management, no dependency on third-party services staying free. It's a perfect complement to a self-hosted dashboard -- pair it with a [system monitoring dashboard](../self-hosted-terminal-dashboard-btop-glances-bottom-system-monitoring-guide-2026/) to see weather alongside CPU, memory, and network stats. For a personalized information hub, integrate weather data into your [self-hosted homepage dashboard](../self-hosted-homepage-dashboards-homepage-dashy-homarr-guide/) alongside bookmarks, service status, and RSS feeds. If you're building a display-centric setup, check our [e-ink dashboard platforms guide](../2026-06-06-self-hosted-eink-dashboard-platforms-inkycal-trmnl-paperpi/) for always-on weather displays.
## Integrating Weather Data into Home Automation

Terminal weather tools aren't just for humans reading the output -- they're excellent data sources for home automation systems. With a few lines of scripting, you can feed weather conditions into smart home platforms to automate blinds, sprinklers, heating, and notifications.

### wttr.in JSON for Home Assistant

wttr.in's JSON API makes it easy to create a Home Assistant REST sensor. Here's a configuration that pulls current temperature and conditions:

```yaml
# configuration.yaml
sensor:
  - platform: rest
    name: Outdoor Temperature
    resource: https://wttr.in/Beijing?format=j1
    value_template: "{{ value_json.current_condition[0].temp_C }}"
    unit_of_measurement: "C"
    scan_interval: 1800
  - platform: rest
    name: Weather Condition
    resource: https://wttr.in/Beijing?format=j1
    value_template: "{{ value_json.current_condition[0].weatherDesc[0].value }}"
    scan_interval: 1800
```

### ansiweather for Telegram Bot Notifications

Combine ansiweather with a notification system to receive daily weather reports:

```bash
#!/bin/bash
# daily-weather-report.sh -- Send weather to Telegram
WEATHER=$(ansiweather -l "Beijing,CN" -u metric -F)
curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendMessage"   -d "chat_id=$CHAT_ID"   -d "text=Good morning! Today's weather: $WEATHER"
```

### wego for Status Panels

wego's table output formats cleanly for dashboard panels. Pipe it to a file and serve with any HTTP server:

```bash
# Generate weather panel and save as text
wego Beijing > /var/www/weather-panel.txt 2>&1

# Or convert to SVG with aha for web display
wego Beijing | aha > /var/www/weather-panel.html
```

### Automated Actions Based on Weather

```bash
#!/bin/bash
# Close blinds if wind speed exceeds threshold
WIND=$(curl -s "wttr.in/Beijing?format=%w")
if [ "${WIND%km/h}" -gt 40 ]; then
    mosquitto_pub -t "home/blinds/all" -m "CLOSE"
fi

# Skip sprinkler if rain is forecast
FORECAST=$(ansiweather -f 2)
if echo "$FORECAST" | grep -qi "rain"; then
    echo "Rain forecast -- skipping sprinkler"
    exit 0
fi
/usr/local/bin/run-sprinklers.sh
```

These integrations transform terminal weather tools from passive information displays into active components of a smart home -- all without cloud dependencies or subscription fees.


## FAQ

### Does wttr.in work without an internet connection?

The public wttr.in service requires internet access to fetch weather data. However, if you self-host wttr.in on your local network, you can access it without internet -- though the self-hosted instance still needs internet to fetch weather data from upstream providers.

### Can I use wego without an API key?

No. wego requires an API key from OpenWeatherMap (free tier: 1,000 calls/day) or WorldWeatherOnline. The free OpenWeatherMap tier is sufficient for personal use -- checking the weather a few times per hour stays well within limits.

### How accurate is terminal weather data?

Terminal weather tools use the same data sources as commercial weather apps -- Open-Meteo (wttr.in default), OpenWeatherMap, and WorldWeatherOnline. Accuracy depends on your chosen provider and location. OpenWeatherMap has good global coverage; Open-Meteo provides excellent European data.

### Can I customize wttr.in's appearance when self-hosting?

Yes. The self-hosted Docker image supports environment variables for default location, language, and units. You can also modify the source code for deeper customization -- wttr.in is written in Go with clean separation between data fetching and rendering.

### Is ansiweather maintained?

ansiweather is a mature, stable project. At 1,942 stars and last updated in December 2025, it's in maintenance mode -- the author addresses bugs and API compatibility but doesn't add major new features. For most users, this stability is a feature, not a bug.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Terminal Weather Tools: wttr.in vs wego vs ansiweather -- Check Weather Without Apps or APIs",
  "description": "Compare three terminal weather tools: wttr.in (self-hostable weather service with Docker), wego (rich TUI forecast), and ansiweather (shell-native weather for scripts). Includes Docker Compose configs and integration examples.",
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
      "url": "https://pistack.xyz/logo.png"
    }
  }
}
</script>
