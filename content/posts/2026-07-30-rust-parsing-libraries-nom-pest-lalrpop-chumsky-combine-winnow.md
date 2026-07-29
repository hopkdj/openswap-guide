---
title: "Rust Parsing Libraries Compared: nom vs pest vs lalrpop vs chumsky vs combine vs winnow"
date: "2026-07-30"
tags: ["rust", "parsing", "parser", "rust-crates", "parser-generator", "comparison", "nom", "pest", "lalrpop", "compiler-tools"]
draft: false
---

Parsing is one of the most common tasks in systems programming — whether you're building a configuration file reader, a protocol decoder, a domain-specific language (DSL), or a full-blown compiler frontend. Rust's strong type system and zero-cost abstractions make it an ideal language for building fast, safe parsers. The ecosystem has responded with a rich selection of parsing libraries spanning multiple paradigms: parser combinators, parser generators, PEG-based engines, and more.

In this article, we compare six of the most popular Rust parsing libraries — **nom**, **pest**, **lalrpop**, **chumsky**, **combine**, and **winnow** — across API design, performance, error messages, learning curve, and ecosystem maturity.

## Comparison Table

| Library | Approach | Stars | Last Updated | Error Messages | Learning Curve | Best For |
|----------|----------|-------|-------------|----------------|----------------|----------|
| nom | Parser Combinator | 10,439 | Aug 2025 | Good (custom) | Medium | Binary + text parsing |
| pest | PEG Grammar | 5,372 | Jul 2026 | Excellent | Easy | Text/DSL parsing |
| lalrpop | LR(1) Generator | 3,495 | Jul 2026 | Good | Medium-High | Programming languages |
| chumsky | Parser Combinator | 4,542 | Mar 2026 | Excellent | Medium | Error-tolerant parsing |
| combine | Parser Combinator | 1,362 | Feb 2026 | Good | Easy-Medium | General parsing |
| winnow | Parser Combinator | 932 | Jul 2026 | Good | Easy-Medium | Lightweight parsing |

## nom: The Battle-Tested Workhorse

[nom](https://github.com/Geal/nom) is the oldest and most widely-used Rust parsing library, with over 10,000 GitHub stars. It pioneered the parser combinator approach in Rust and excels at parsing binary formats, network protocols, and structured text.

Key features include support for streaming input, zero-copy parsing, and extensive combinators for bytes, bits, and strings.

```rust
use nom::{
    IResult,
    bytes::complete::{tag, take_while_m_n},
    combinator::map_res,
    sequence::tuple,
};

#[derive(Debug, PartialEq)]
struct Color {
    red: u8,
    green: u8,
    blue: u8,
}

fn hex_primary(input: &str) -> IResult<&str, u8> {
    map_res(
        take_while_m_n(2, 2, |c: char| c.is_ascii_hexdigit()),
        |s| u8::from_str_radix(s, 16),
    )(input)
}

fn hex_color(input: &str) -> IResult<&str, Color> {
    let (input, _) = tag("#")(input)?;
    let (input, (red, green, blue)) = tuple((hex_primary, hex_primary, hex_primary))(input)?;
    Ok((input, Color { red, green, blue }))
}

fn main() {
    assert_eq!(
        hex_color("#2F14DF"),
        Ok(("", Color { red: 47, green: 20, blue: 223 }))
    );
}
```

Nom's combinator API is explicit and composable, but error messages can be verbose and difficult to trace.

## pest: Grammar-First, Error-First

[pest](https://github.com/pest-parser/pest) uses a separate grammar file written in a PEG-like syntax. The grammar is processed at compile time into Rust code, giving you full type safety and excellent error messages out of the box.

```pest
// grammar.pest
WHITESPACE = _{ " " | "	" | "" | "
" }

date = { year ~ "-" ~ month ~ "-" ~ day }
year = { ASCII_DIGIT{4} }
month = { ASCII_DIGIT{2} }
day = { ASCII_DIGIT{2} }

main = { SOI ~ date ~ EOI }
```

```rust
use pest::Parser;
use pest_derive::Parser;

#[derive(Parser)]
#[grammar = "grammar.pest"]
struct DateParser;

fn main() {
    let result = DateParser::parse(Rule::date, "2026-07-30");
    match result {
        Ok(pairs) => println!("Parsed successfully: {:?}", pairs),
        Err(e) => eprintln!("Parse error: {}", e),
    }
}
```

Pest's error messages are the gold standard in the Rust parsing ecosystem, with precise location markers and expected-token suggestions. The trade-off is that the grammar must be defined in a separate file, and the compile-time code generation adds build complexity.

## lalrpop: For Programming Language Authors

[lalrpop](https://github.com/lalrpop/lalrpop) takes a different approach: it generates LR(1) parsers (the same class used by yacc/bison) but with Rust-native syntax and strong type safety. It is the go-to choice for implementing programming languages and complex DSLs.

```rust
// calculator.lalrpop
use std::str::FromStr;

grammar;

pub Expr: i32 = {
    <n: Num> => n,
    "(" <e: Expr> ")" => e,
    <l: Expr> "+" <r: Expr> => l + r,
    <l: Expr> "-" <r: Expr> => l - r,
    <l: Expr> "*" <r: Expr> => l * r,
    <l: Expr> "/" <r: Expr> => l / r,
};

Num: i32 = <s: r"[0-9]+"> => i32::from_str(s).unwrap();
```

Lalrpop's grammar files are expressive and readable, but LR(1) parser generators have a steeper learning curve and require understanding of shift-reduce conflicts and associativity declarations.

## chumsky: Error Recovery and Diagnostics

[chumsky](https://github.com/zesterer/chumsky) is a relatively newer parser combinator library designed from the ground up for error recovery and user-friendly diagnostics. It supports error-tolerant parsing — meaning it can continue parsing after encountering errors and report multiple issues at once, similar to how Rust's own compiler produces multiple error messages in a single run.

```rust
use chumsky::prelude::*;

#[derive(Debug)]
enum Expr {
    Num(f64),
    Add(Box<Expr>, Box<Expr>),
    Sub(Box<Expr>, Box<Expr>),
}

fn parser() -> impl Parser<char, Expr, Error = Simple<char>> {
    let num = text::int(10)
        .from_str()
        .unwrapped()
        .map(Expr::Num);

    let expr = recursive(|expr| {
        let atom = num.or(expr.delimited_by(just('('), just(')')));
        let op = just('+').to(Expr::Add as fn(_, _) -> _)
            .or(just('-').to(Expr::Sub as fn(_, _) -> _));
        atom.clone().then(op.then(atom).repeated()).foldl(|a, (op, b)| op(Box::new(a), Box::new(b)))
    });

    expr.then_ignore(end())
}
```

Chumsky's standout feature is its ability to produce multiple error messages with visual underlines and suggestions, rivaling pest in error quality while keeping a combinator-based API.

## combine: The Pragmatic Middle Ground

[combine](https://github.com/Marwes/combine) strikes a balance between nom's explicitness and pest's ergonomics. It supports both `&str` and `&[u8]` input, offers a macro-based shorthand, and provides readable error types.

```rust
use combine::{
    parser::char::{char, digit, spaces},
    choice, many1, Parser,
};

fn integer() -> impl Parser<char, i32> {
    many1(digit())
        .map(|s: String| s.parse::<i32>().unwrap())
}

fn expr() -> impl Parser<char, i32> {
    let term = integer().or(
        char('(').with(spaces()).with(expr()).skip(spaces()).skip(char(')')))
    );
    let op = char('+').or(char('-')).skip(spaces());
    term.and(choice((op, term)).skip(spaces()).map(|(op, rhs)| (op, rhs)))
        .foldl(|lhs, (op, rhs)| match op {
            '+' => lhs + rhs,
            '-' => lhs - rhs,
            _ => unreachable!(),
        })
}
```

Combine's API is clean and functional, making it a good choice for developers who want combinator power without nom's sometimes-cryptic type signatures.

## winnow: Lightweight and Modern

[winnow](https://github.com/winnow-rs/winnow) is a modern fork of nom designed to be simpler, faster to compile, and easier to debug. It reduces the trait complexity of nom's type system while maintaining the same streaming and zero-copy guarantees.

```rust
use winnow::{
    Parser,
    ascii::{dec_uint, multispace0},
    combinator::{delimited, preceded, separated_pair},
    token::tag,
};

fn parse_key_value(input: &mut &str) -> winnow::Result<(&str, u32)> {
    separated_pair(
        winnow::token::take_till(1.., |c| c == ':'),
        tag(":"),
        preceded(multispace0, dec_uint),
    )
    .parse_next(input)
}

fn main() -> winnow::Result<()> {
    let mut input = "port: 8080";
    let (key, value) = parse_key_value(&mut input)?;
    println!("{} = {}", key, value);
    Ok(())
}
```

Winnow also provides migration guides from nom, making it easy for existing nom users to transition.

## Why Self-Host Your Parsing Toolchain?

Choosing the right parsing library is a foundational engineering decision. Unlike web frameworks where you can swap out components, a parser is deeply integrated into your application's data flow — changing it often means rewriting significant portions of your codebase. By understanding the trade-offs upfront, you can select the library that best matches your project's needs for years to come.

Rust's parsing ecosystem is unique in its diversity: you have the precision of LR(1) generators (lalrpop), the elegance of PEG grammars (pest), the raw power of parser combinators (nom/chumsky/combine/winnow), and each serves different use cases. For related Rust library comparisons, see our [Rust logging libraries guide](../2026-07-27-rust-logging-libraries-env-logger-log4rs-tracing-slog/) and [Rust web frameworks comparison](../2026-07-13-rust-web-frameworks-actix-web-rocket-axum/). For pattern matching at the string level rather than the grammar level, check our [regular expression engine comparison](../2026-06-22-regular-expression-engine-libraries-re2-pcre2-hyperscan-oniguruma-guide/).

## FAQ

### When should I use a parser combinator vs a parser generator?

Parser combinators (nom, combine, chumsky, winnow) are best when you need full control over the parsing process, are building binary protocol parsers, or want to avoid a build-time code generation step. Parser generators (pest, lalrpop) are better when you want a declarative grammar that closely matches a formal specification, or when you need guaranteed correctness for complex grammars like programming languages.

### Which library produces the best error messages?

Pest and chumsky are tied for best-in-class error messages. Pest's compile-time grammar analysis produces precise, location-aware errors with expected token suggestions. Chumsky supports error recovery and can report multiple errors simultaneously with visual underlines — ideal for tools like linters and language servers where showing all errors at once improves developer experience.

### Is nom still maintained?

Nom's last release was in August 2025, and while it remains functional and battle-tested, its development has slowed. For new projects, consider winnow (a simplified nom fork with active maintenance) or chumsky (for error-tolerant parsing needs). Nom's 10,000+ stars and mature documentation still make it a solid choice for projects that need maximum stability.

### Can I mix parsing libraries in the same project?

Yes, Rust's crate system makes it easy to use multiple parsing libraries in the same project. For example, you might use pest for parsing user-facing configuration files (where error messages matter most) and nom for parsing binary network protocols (where zero-copy performance matters). Each library operates independently, and their types don't conflict.

### What about serde for parsing?

[Serde](https://serde.rs/) is the standard Rust serialization framework, not a general-purpose parsing library. It's excellent for deserializing JSON, YAML, TOML, and other structured formats with known schemas, but it cannot handle context-free grammars, streaming protocols, or formats without a defined data model. Use parsing libraries when you need grammar-level control; use serde when you have structured data with a known schema.

---

**Want to test your market judgment? I use [Polymarket](https://polymarket.com/?r=fc8a0) for prediction market trading — the world's largest prediction market platform. From election results to tech regulatory timelines, you can bet on anything. Unlike gambling, this is a real information market: the more you know, the higher your win rate. I've made solid returns predicting tech-related event outcomes. Sign up with my referral link:** [Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rust Parsing Libraries Compared: nom vs pest vs lalrpop vs chumsky vs combine vs winnow",
  "description": "Comprehensive comparison of six Rust parsing libraries across API design, performance, error messages, and learning curve. Includes code examples for nom, pest, lalrpop, chumsky, combine, and winnow.",
  "datePublished": "2026-07-30",
  "dateModified": "2026-07-30",
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
