---
title: "Self-Hosted CLI Dictionary and Translation Tools: translate-shell vs sdcv vs dictd — Offline Language Lookup for Your Terminal"
date: "2026-06-17"
tags: ["cli-tools", "translation", "dictionary", "language", "terminal", "self-hosted"]
draft: false
---

## Why Use CLI Dictionary and Translation Tools?

When you're deep in terminal work, switching to a browser to look up a word or translate a phrase breaks your flow. CLI dictionary and translation tools let you resolve language questions without leaving the keyboard -- and unlike browser-based translators, they can work entirely offline when paired with local dictionary servers.

Whether you're reading foreign-language documentation, writing multilingual code comments, or learning a new language, having instant dictionary access in your terminal is a productivity multiplier. In this guide, we compare three approaches: **translate-shell** (online translation CLI), **sdcv** (offline StarDict client), and **dictd** (self-hosted dictionary server protocol).

## Comparison Table: translate-shell vs sdcv vs dictd

| Feature | translate-shell | sdcv | dictd |
|---------|----------------|------|-------|
| **Stars** | 7,472 | 362 | Protocol (multiple servers) |
| **Language** | Awk | C++ | C/Rust/Go (servers) |
| **Type** | Online translation CLI | Offline dictionary client | Dictionary server protocol |
| **Works offline** | No | Yes | Yes (self-hosted) |
| **Providers** | Google, Bing, Yandex, DeepL, Apertium | StarDict dictionaries | RFC 2229 dictionaries |
| **Languages** | 100+ via Google Translate | Depends on installed dicts | Depends on installed dicts |
| **Install size** | ~50KB | ~200KB + dictionaries | ~1-5MB + dictionaries |
| **Self-hostable** | No (relies on external APIs) | N/A (local only) | Yes (dictd server) |
| **Output** | Plain text, JSON, speech | Plain text | Plain text |
| **Dependencies** | gawk, curl | glib2, zlib | dictd server or client |
| **Best for** | Quick translations | Offline dictionary lookups | Team dictionary servers |

## translate-shell: Instant Online Translation

[translate-shell](https://github.com/soimort/translate-shell) (formerly Google Translate CLI) is the most popular command-line translation tool with over 7,400 stars. It's a single Awk script that wraps multiple translation engines -- Google Translate, Bing Translator, Yandex.Translate, DeepL, and Apertium.

### Installation

```bash
# Ubuntu/Debian
sudo apt install translate-shell

# macOS
brew install translate-shell

# From source
git clone https://github.com/soimort/translate-shell.git
cd translate-shell
sudo make install
```

### Basic Translation

```bash
# Translate a word to Chinese
trans :zh "hello world"
# Output: 你好世界

# Translate from Chinese to English
trans :en "你好世界"

# Auto-detect source language
trans "Bonjour le monde"

# Brief mode (translation only)
trans -b :zh "open source software"
# Output: 开源软件

# Multiple target languages
trans :zh+ja+ko "hello"
```

### Advanced Features

```bash
# JSON output for scripting
trans -j :en "bonjour" | jq '.[0][0][0]'

# Text-to-speech output
trans -speak :en "Linux is everywhere"

# Dictionary mode (definitions, synonyms)
trans -d "ubiquitous"

# Translate a file
trans :zh file://README.md -o README_zh.md

# Interactive shell
trans -shell -brief :zh
```

### Shell Integration

Add translation to your workflow with shell functions:

```bash
# Add to ~/.bashrc
alias ten="trans -b :en"
alias tzh="trans -b :zh"

# Translate last command output
ls --help | trans :zh -b

# Quick lookup while reading logs
tail -f /var/log/syslog | grep -i error | trans :zh -b
```

The main limitation of translate-shell is its reliance on external APIs -- it requires internet access and is subject to rate limits. For offline use, you need a different approach.

## sdcv: Offline StarDict Dictionary Client

[sdcv](https://github.com/Dushistov/sdcv) (StarDict Console Version) is a command-line client for the StarDict dictionary format. It works entirely offline -- you download dictionary files once and look up words locally forever.

### Installation

```bash
# Ubuntu/Debian
sudo apt install sdcv

# macOS
brew install sdcv

# Build from source
git clone https://github.com/Dushistov/sdcv.git
cd sdcv
cmake . && make
sudo make install
```

### Installing Dictionaries

StarDict dictionaries are `.idx` / `.dict` / `.ifo` file triples. Download them from community sources:

```bash
# Create dictionary directory
mkdir -p ~/.stardict/dic

# Download English-Chinese dictionary (example)
cd ~/.stardict/dic
wget http://download.huzheng.org/zh_CN/stardict-langdao-ec-gb-2.4.2.tar.bz2
tar xjf stardict-langdao-ec-gb-2.4.2.tar.bz2

# Download WordNet English dictionary
wget http://download.huzheng.org/dict.org/stardict-dictd_www.dict.org_gcide-2.4.2.tar.bz2
tar xjf stardict-dictd_www.dict.org_gcide-2.4.2.tar.bz2
```

### Usage

```bash
# Word lookup
sdcv "algorithm"
# Output: Definitions from all installed dictionaries

# Search with regex
sdcv -e "algo.*"

# List installed dictionaries
sdcv -l

# Use a specific dictionary
sdcv -u "朗道英汉字典5.0" "paradigm"
```

sdcv's strength is its completely offline operation. Once dictionaries are downloaded, no network is needed. This makes it ideal for air-gapped environments, travel, or situations where internet access is unreliable.

### Docker-Based Dictionary Server with sdcv

You can containerize sdcv for consistent deployments:

```yaml
# docker-compose.yml -- Containerized sdcv dictionary server
version: "3.8"
services:
  dictionary:
    image: ubuntu:22.04
    container_name: sdcv-server
    command: |
      bash -c "
        apt-get update && apt-get install -y sdcv wget bzip2 openssh-server &&
        mkdir -p /root/.stardict/dic &&
        cd /root/.stardict/dic &&
        wget http://download.huzheng.org/dict.org/stardict-dictd_www.dict.org_gcide-2.4.2.tar.bz2 &&
        tar xjf stardict-dictd_www.dict.org_gcide-2.4.2.tar.bz2 &&
        service ssh start &&
        tail -f /dev/null
      "
    volumes:
      - ./dictionaries:/root/.stardict/dic
```

## dictd: Self-Hosted Dictionary Server Protocol

[dictd](https://en.wikipedia.org/wiki/DICT) is a network dictionary server protocol defined in RFC 2229 (1997). It may be old, but its client-server architecture makes it the most scalable approach for team dictionary access. A single dictd server can serve dozens of dictionaries to multiple users over the network.

### Server Setup

```bash
# Install dictd server
sudo apt install dictd dict-gcide dict-moby-thesaurus

# Verify dictionaries are installed
ls /usr/share/dictd/

# Start the server
sudo systemctl start dictd
sudo systemctl enable dictd
```

### Client Usage

```bash
# Install dict client
sudo apt install dict

# Query local server
dict "linux"

# Query a specific dictionary
dict -d gcide "algorithm"

# Query a remote server
dict -h dict.org "open source"

# List available dictionaries on server
dict -D
```

### Self-Hosted dictd with Docker

Run a complete dictd server with pre-loaded dictionaries:

```yaml
# docker-compose.yml
version: "3.8"
services:
  dictd:
    image: ubuntu:22.04
    container_name: dictd-server
    ports:
      - "2628:2628"
    command: |
      bash -c "
        apt-get update &&
        DEBIAN_FRONTEND=noninteractive apt-get install -y dictd dict-gcide dict-wn dict-moby-thesaurus &&
        echo 'access { allow * }' >> /etc/dictd/dictd.conf &&
        dictd -d nodetach
      "
    restart: unless-stopped
```

```bash
docker compose up -d
dict -h localhost "algorithm"  # Query your self-hosted server
```

### Extended Dictionary Setup

For multilingual or domain-specific dictionaries, add custom DICT-format files:

```bash
# Install additional free dictionaries
sudo apt install dict-freedict-eng-spa dict-freedict-eng-fra dict-freedict-eng-deu

# Verify they're available
dict -D | grep freedict
dict -d fd-eng-spa "hello"
# Output: hola
```

## Choosing the Right Tool

| Scenario | Recommendation |
|----------|---------------|
| Quick translation between languages | translate-shell |
| Offline word definitions | sdcv with StarDict files |
| Team dictionary server | dictd |
| Educational/language learning | sdcv (custom dictionaries) |
| Script translation automation | translate-shell (JSON mode) |
| Air-gapped environments | sdcv or dictd |
| Both translation AND definition | translate-shell + sdcv together |

## Why Self-Host Your Dictionary Service?

Running your own dictd server ensures consistent, private dictionary access across your team or household. Unlike cloud translation services, no query logs leave your network. It's an excellent complement to [self-hosted language learning platforms](../2026-06-12-self-hosted-language-learning-platforms-librelingo-lute-tatoeba/) -- pair offline dictionaries with interactive language tools for a complete learning environment. For researchers working with multilingual corpora, integrate dictionary lookups into your [text mining pipeline](../2026-06-15-text-mining-platforms-voyant-gate-uima/) for automated term extraction and definition retrieval. Linguistic researchers will also find our [corpus linguistics guide](../2026-06-14-self-hosted-corpus-linguistics-blacklab-kontext-annis/) useful for building and querying large text collections.

## FAQ

### Does translate-shell work without an internet connection?

No. translate-shell requires internet access to call translation APIs (Google, Bing, Yandex, DeepL). For offline use, install sdcv with local dictionary files or set up a local dictd server.

### How large are StarDict dictionary files?

English dictionaries typically range from 5-50MB. Multilingual dictionaries (English-Chinese, English-Japanese) are larger at 50-200MB. You can install only the dictionaries you need -- sdcv supports selective dictionary use with the `-u` flag.

### Can I add custom dictionaries to sdcv?

Yes. sdcv uses the StarDict format, which is well-documented. You can create custom dictionaries from CSV files using tools like `stardict-editor` or `pyglossary`. This is useful for domain-specific terminology -- legal, medical, or engineering glossaries.

### Is dictd still maintained?

dictd as a protocol (RFC 2229) is stable and hasn't changed since 1997. Server implementations are maintained in various Linux distributions (Debian, Ubuntu, Fedora). The `dictd` package receives security updates and bug fixes but doesn't undergo active feature development.

### Can I use translate-shell with a self-hosted translation service?

translate-shell supports the Apertium backend, which is a rule-based machine translation system that can be self-hosted. For neural translation, projects like LibreTranslate offer self-hosted alternatives, though translate-shell doesn't natively support them -- you'd need to write a wrapper script.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted CLI Dictionary and Translation Tools: translate-shell vs sdcv vs dictd -- Offline Language Lookup for Your Terminal",
  "description": "Compare three CLI dictionary and translation tools: translate-shell (online translation CLI), sdcv (offline StarDict client), and dictd (self-hosted dictionary server protocol). Includes Docker Compose configs for self-hosted dictionary servers.",
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
