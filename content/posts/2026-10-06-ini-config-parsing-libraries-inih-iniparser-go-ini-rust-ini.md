---
title: "INI Files in 2026: inih vs iniparser vs go-ini vs rust-ini — Which Config Parser Should You Actually Ship?"
date: "2026-10-06"
tags: ["configuration", "developer-tools", "parsing"]
draft: false
---

INI is the configuration format everyone declares dead and nobody stops using. It runs systemd units, Windows applications, PHP's `php.ini`, embedded firmware, and roughly every game engine's settings file. The reason is simple: **a human can edit INI without a manual, and a parser can read it in a few hundred bytes of code.** That second property is why `inih` exists — a complete INI parser in under 200 lines of C, which is why it ended up inside thousands of embedded projects.

The problem is that "INI" is not a standard. There is no specification, only a family of mutually incompatible dialects. `;` comments here, `#` comments there. Keys lowercased in one parser and case-sensitive in the next. Type coercion from nothing at all. This guide compares the parsers you would realistically ship in 2026 with live GitHub data, working code, and the dialect differences that will actually bite you.

## TL;DR / Quick Verdict

**C or C++, or anything embedded? Use `inih`.** It is 3,042 stars, actively maintained (last push September 2026), has zero dependencies, and compiles to almost nothing. It is read-only, which is usually the right call for firmware.

**Need to read *and write* INI from C? Use `iniparser`.** It ships a dictionary API with typed getters and can serialise back out, at the cost of a much larger footprint than `inih`.

**Go service? Use `go-ini/ini`.** 3,543 stars, the most feature-complete parser in this comparison — multiple data sources, parent-child sections, comment preservation, and struct mapping.

**Rust? Use `rust-ini`.** Only 344 stars, and that is not a sign of quality — it is the reality of the Rust INI ecosystem. It is the only maintained option and it supports both reading and writing.

**Python and JavaScript? Use the standard library or the npm default.** Python's `configparser` and the widely used `ini` package are adequate; the third-party alternatives offer comfort, not capability.

## The Comparison Table

Live GitHub data pulled 2026-10-06:

| Parser | Language | Stars | Last push | Read | Write | Typed getters | Comments in | Case-sensitive keys |
|---|---|---|---|---|---|---|---|---|
| [benhoyt/inih](https://github.com/benhoyt/inih) | C | **3,042** | 2026-09-27 | Yes | **No** | No (callback) | `;` (configurable) | Yes |
| [ndevilla/iniparser](https://github.com/ndevilla/iniparser) | C | **1,076** | 2026-10-03 | Yes | Yes | Yes | `;` and `#` | Yes |
| [go-ini/ini](https://github.com/go-ini/ini) | Go | **3,543** | 2026-09-05 | Yes | Yes | Yes | `;` and `#` | Yes (configurable) |
| [zonyitoo/rust-ini](https://github.com/zonyitoo/rust-ini) | Rust | **344** | 2026-08-26 | Yes | Yes | Partial | `;` and `#` | Yes |
| [npm/ini](https://github.com/npm/ini) | JavaScript | **820** | 2026-07-02 | Yes | Yes | No | `;` and `#` | Yes |
| Python `configparser` | Python | stdlib | — | Yes | Yes | Yes | `;` and `#` | **No — lowercases** |
| [DiffSK/configobj](https://github.com/DiffSK/configobj) | Python | **337** | 2026-08-19 | Yes | Yes | Yes | `;` and `#` | No (configurable) |

Two things jump out. First, **all four actively maintained implementations had commits within the last six weeks** — this format is not going anywhere. Second, **Python's stdlib parser is the only one that silently lowercases your keys**, and that single behaviour causes more cross-language configuration bugs than any other difference on this page.

## Decision Matrix: Pick in 10 Seconds

| Situation | Recommendation | Why |
|---|---|---|
| Firmware, embedded, no allocator | inih with `INI_USE_STACK=1` | ~200 LOC, no `malloc`, no dependencies |
| C application that edits its own config | iniparser | Dictionary API with typed getters and write-back |
| Go service with env + file + struct mapping | go-ini/ini | Loads from file, `[]byte`, and `io.Reader`; can map to structs |
| Rust CLI or daemon | rust-ini | The only maintained option; read and write |
| Node tooling | the `ini` package | Default in the npm ecosystem, stable API |
| Python app, simple config | stdlib `configparser` | Zero dependencies, typed getters built in |
| Python app needing nested sections and types | configobj | Sections nest, values keep their types |
| Config that a machine also writes | **not INI — use TOML or JSON** | See the TOML comparison linked below |

The last row deserves emphasis. INI has no escaping rules, no nesting, no arrays, and no types. If your program writes the config file, pick a format with a specification.

## inih: The Minimalist Choice

`inih` inverts the usual parser API. It does not return a tree — you supply a callback and it invokes it once per key/value pair as it streams the file:

```c
#include <stdio.h>
#include <string.h>
#include "ini.h"

static int handler(void* user, const char* section,
                   const char* name, const char* value)
{
    if (strcmp(section, "protocol") == 0 && strcmp(name, "version") == 0) {
        *(int*)user = atoi(value);
    } else {
        /* unknown key — decide whether to warn or ignore */
    }
    return 1;   /* non-zero means success; 0 aborts parsing */
}

int main(void)
{
    int version = 0;
    if (ini_parse("test.ini", handler, &version) < 0) {
        fprintf(stderr, "can't load 'test.ini'\n");
        return 1;
    }
    printf("Protocol version = %d\n", version);
    return 0;
}
```

The callback design is why the library fits in embedded projects: **no dynamic allocation, no tree to free, and you only pay for the keys you actually read.** Compile-time defines control the memory and dialect behaviour:

| Define | Effect |
|---|---|
| `INI_MAX_LINE` | Maximum line length (default 200 bytes) |
| `INI_ALLOW_MULTILINE` | Allow values continued with a trailing backslash |
| `INI_USE_STACK` | Use the stack instead of heap for line buffering |
| `INI_ALLOW_REALLOC` | Permit heap growth for over-long lines |
| `INI_START_COMMENT_PREFIXES` | Characters that begin a comment (default `;`) |

That last define is the dialect trap. **`inih` treats only `;` as a comment by default**, so a config file that another tool wrote with `#` comments will not parse the way you expect. Set `INI_START_COMMENT_PREFIXES` to `";#"` if you need both.

## iniparser: Dictionary and Typed Getters

`iniparser` is the opposite philosophy: parse everything into a dictionary you can query by `"section:key"` paths, then free it. It costs more memory but gives you a friendlier API and, crucially, can write the file back.

```c
#include <stdio.h>
#include "iniparser.h"

int main(void)
{
    dictionary* ini = iniparser_load("example.ini");
    if (ini == NULL) return 1;

    /* Typed getters — each takes a default for missing keys */
    const char* name = iniparser_getstring(ini, "user:name", "unknown");
    int         port = iniparser_getint(ini, "network:port", 8080);
    double        pi = iniparser_getdouble(ini, "physics:pi", 3.14);
    int        debug = iniparser_getboolean(ini, "debug:enabled", 0);

    printf("user=%s port=%d pi=%f debug=%d\n", name, port, pi, debug);

    /* Mutate and dump back out */
    iniparser_set(ini, "network:port", "9090");
    iniparser_dump_ini(ini, stdout);

    iniparser_freedict(ini);
    return 0;
}
```

Two operational notes. `iniparser` uses `"section:key"` colon paths rather than separate arguments, and it is **not fully Unicode-safe** — the parser operates on bytes, so a UTF-8 BOM at the start of the file and multi-byte values need care. Verify round-trip behaviour with your real config before trusting it.

## go-ini: The Most Feature-Complete Parser

`go-ini` is the outlier in this comparison: it is a configuration *framework*, not just a parser. It loads from multiple sources with overwrite precedence, preserves comments, and can map sections onto Go structs.

```go
package main

import (
	"fmt"
	"log"

	"gopkg.in/ini.v1"
)

func main() {
	cfg, err := ini.Load("my.ini")
	if err != nil {
		log.Fatalf("failed to load config: %v", err)
	}

	/* Global section is the empty string */
	appName := cfg.Section("").Key("app_name").String()

	/* Typed accessors parse and convert for you */
	port, _ := cfg.Section("mysql").Key("port").Int()
	password := cfg.Section("mysql").Key("password").String()

	fmt.Println(appName, port, len(password))

	/* Mutate and save, keeping section and key order */
	cfg.Section("path").Key("tmp").SetValue("/tmp")
	if err := cfg.SaveTo("my.ini"); err != nil {
		log.Fatal(err)
	}
}
```

The feature that separates `go-ini` from everything else here is `MapTo`, which binds a section directly onto a struct. For a service with twenty settings, that removes twenty lines of string-key lookups — and, more importantly, removes twenty chances to typo a key name. It also supports loading several files in order so that `config.default.ini` and `config.local.ini` merge, which is a pattern every deployment eventually needs.

## rust-ini: Writing Config From Rust

`rust-ini` supports the full read/write cycle with a builder-style API:

```rust
use ini::Ini;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Reading
    let conf = Ini::load_from_file("conf.ini")?;
    let user = conf.section(Some("User")).unwrap();
    println!("{}", user.get("given_name").unwrap_or("anonymous"));

    // Writing
    let mut out = Ini::new();
    out.with_section(None::<String>).set("encoding", "utf-8");
    out.with_section(Some("User"))
        .set("given_name", "Tommy")
        .set("family_name", "Green");
    out.write_to_file("conf.ini")?;

    Ok(())
}
```

Note `with_section(None::<String>)` for the global section. That explicit `None` type annotation is required because the API needs to know you are not passing a section name, and it is the single most common compile error newcomers hit with this crate.

## JavaScript and Python: The Defaults Are Fine

The `ini` package is what npm itself used for a decade, and its API is the smallest of any parser here:

```js
import { parse, stringify } from 'ini';

const config = parse(text);       // sections become nested objects
console.log(config.database.user);   // strings all the way down

const output = stringify(config);    // write it back
```

Section-less keys become top-level properties. Nested sections (`[paths.default]`) become nested objects. Values are always strings — `ini` does no type coercion at all, which is honest but means `port: 8080` arrives as `'8080'` and you must convert.

Python's stdlib parser does coerce, and that is exactly where the most common production bug lives:

```python
import configparser

# Always disable interpolation unless you have verified it is safe
cfg = configparser.ConfigParser(interpolation=None)
cfg.read('my.ini')

name = cfg['user']['name']
port = cfg.getint('network', 'port')        # int
debug = cfg.getboolean('debug', 'enabled')  # bool
```

For nested sections and type-preserving values, `configobj` is the upgrade path:

```python
from configobj import ConfigObj

cfg = ConfigObj('my.ini')
print(cfg['user']['name'])
print(cfg['network']['port'])   # still a string unless you supply a configspec
```

Adjacent reading worth doing: our [TOML parsing libraries comparison](../2026-09-27-toml-parsing-libraries-tomllib-tomlkit-toml-rs-go-toml-comparison/) covers the format you should choose when your application writes its own config, the [YAML parsing libraries comparison](../2026-06-20-yaml-parsing-libraries-pyyaml-serdayaml-jsyaml-snakeyaml-libyaml/) covers the Kubernetes-shaped alternative, and for application-level configuration layering see the [Go configuration libraries guide](../2026-06-21-application-configuration-libraries-viper-koanf-configrs-typesafe/) and the [Node.js config libraries comparison](../2026-08-23-nodejs-config-libraries-dotenv-envalid-node-config-comparison/).

## Common Pitfalls

**1. `%` interpolation in Python `configparser`.** The default interpolator treats `%` as a substitution marker, so a password of `p%40ss` or a SQL `LIKE '%foo%'` raises `InterpolationSyntaxError` at read time. Pass `interpolation=None`. This one bug probably accounts for more INI-related production incidents than everything else combined.

**2. Case folding across languages.** Python lowercases keys; `inih`, `iniparser`, `go-ini`, and `rust-ini` do not. A config written by a Go service and read by Python can break purely because of capitalisation. Pick one convention and enforce it.

**3. Duplicate keys.** Most parsers take the last value silently; `iniparser` and `configparser` treat duplicates as errors or overwrite depending on configuration. If the file is generated by humans, decide explicitly rather than inheriting a library default.

**4. `DEFAULT` section inheritance.** In `configparser`, a `[DEFAULT]` section is inherited by *every* other section. That is occasionally useful and routinely surprising, particularly when a default key appears in a section you thought you had fully specified.

**5. Comment prefixes you did not choose.** `;` versus `#`, whether they must start a line or can be inline, and whether the comment survives a round-trip all vary. `inih` is read-only so it does not matter there, but `go-ini` and `configobj` can preserve comments — a useful feature that silently corrupts files when you assume the other parser does the same.

**6. No escaping means no way to express a value that looks like syntax.** There is no escape sequence for a `#` at the start of a value, or for a `[` inside a key. If a user-supplied string can land in a config file, you have an injection surface. Validate and reject rather than escape.

**7. Assuming a spec exists.** There is no INI RFC. Windows `GetPrivateProfileString`, systemd, PHP's `parse_ini_file`, and every library here implement different dialects. If your config must be read by more than one of them, test the actual bytes rather than trusting the label "INI".

## FAQ

**Is INI still a good choice for a new project in 2026?**
Yes for small, human-edited, flat configuration — it is trivially readable, has parsers in every language, and needs no dependencies. No for anything your program writes itself, needs nesting in, or must round-trip reliably, because INI has no specification and no escaping rules. For those cases use TOML.

**What is the difference between inih and iniparser?**
`inih` is a single-file streaming parser with a callback API, no dynamic allocation, and no write support — designed for embedded systems. `iniparser` builds a queryable dictionary with typed getters and can serialise back to disk, at the cost of much higher memory use.

**Why do key names sometimes change case after parsing?**
Because Python's `configparser` lowercases keys by default, while the C, Go, Rust, and JavaScript parsers here are case-sensitive. Set `optionxform = str` on the parser to preserve case, or standardise on lowercase keys everywhere.

**Can INI files contain comments, and which character starts one?**
Most parsers accept both `;` and `#`, but `inih` defaults to `;` only, and inline comments are not universally supported. Check the specific parser's configuration before relying on comments surviving a read-write round trip.

**Does INI support arrays or nested sections?**
Not in any portable way. Some parsers fake arrays with repeated keys or indexed names like `server1`, `server2`, and some fake nesting with dot-separated section names like `[paths.default]`. These are conventions, not features, and they do not port between implementations.

**How should I store configuration in an embedded C project?**
Use `inih` with `INI_USE_STACK` enabled and `INI_MAX_LINE` tuned to your longest expected line, so the parser never calls `malloc`. Keep the handler callback small and validate every value, since INI provides no types and no schema.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "INI Files in 2026: inih vs iniparser vs go-ini vs rust-ini — Which Config Parser Should You Actually Ship?",
  "description": "A practical 2026 comparison of INI configuration parsers — inih, iniparser, go-ini, rust-ini, the npm ini package, Python configparser and configobj — with real GitHub stats, working code and dialect pitfalls.",
  "datePublished": "2026-10-06",
  "dateModified": "2026-10-06",
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
