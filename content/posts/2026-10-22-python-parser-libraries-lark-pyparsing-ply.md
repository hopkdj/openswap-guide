---
title: "Lark vs PyParsing vs PLY in 2026: Python Parser Libraries After PLY's Retirement"
date: "2026-10-22"
tags: ["python", "parsing", "developer-tools", "dsl", "compilers"]
description: "Lark, PyParsing and PLY compared for real grammar work in 2026 — including PLY's December 2025 abandonment, LALR vs Earley trade-offs, working code for each library and a migration path."
draft: false
---

On 21 December 2025, David Beazley posted a short notice at the top of the PLY README: after 25 years, he was abandoning the project. No further maintenance. His suggestion for users was to copy the library into their own tree or write a parser by hand. If your codebase still imports `ply.yacc`, that notice is the most important paragraph in your dependency review this quarter.

PLY's retirement leaves Python with two credible grammar libraries — Lark and PyParsing — plus one legacy option that many teams are still running in production. The two survivors take opposite approaches: Lark compiles a declarative grammar into a parser, while PyParsing builds grammars as Python expressions that parse as they go. Choosing between them is not a matter of taste; it depends on whether your problem looks more like a language or more like a log line.

## TL;DR — Quick Verdict

- **You are writing a DSL, a query language, a config format or anything with a real grammar** → **Lark**. Declarative EBNF, both Earley and LALR(1) engines, automatic tree construction, and a standalone parser generator for deployment without the dependency.
- **You are extracting structured data from semi-regular text — logs, CLI output, protocol messages, one-off scraping** → **PyParsing**. Grammars are Python objects, you can build them incrementally in a REPL, and there is no separate grammar language to learn.
- **You maintain PLY code today** → keep it running short-term, but stop adding grammar rules to it. The project receives no fixes, and the parsing table workflow was already the weakest part of the design. Plan a migration to Lark, which is the closest conceptual match.

If you only need to pull three fields out of a well-known log format, use a regular expression and skip all three libraries. Parsers earn their complexity when the input has nesting.

## Head-to-Head Comparison

Repository data pulled live on 22 October 2026.

| Dimension | Lark | PyParsing | PLY |
|---|---|---|---|
| GitHub stars | 6,014 | 2,496 | 2,908 |
| Last push | 2026-08-27 | 2026-10-18 | 2025-12-21 |
| Latest version | 1.3.1 | 3.3.3 | 3.11 |
| Maintenance status | Active | Active | Abandoned (Dec 2025) |
| Grammar style | Declarative EBNF string or `.lark` file | Python combinator expressions | Docstring-embedded rules |
| Algorithms | Earley (incl. SPPF), LALR(1) | PEG-style recursive descent with optional packrat | LALR(1) only |
| Left recursion | Supported (Earley) | Not supported | Supported via grammar |
| Tree construction | Automatic, annotated | Manual via results names | Manual via rule actions |
| Standalone parser export | Yes (`lark.tools.standalone`) | No | Yes (vendored source) |
| Dependencies | None | None | None |
| Licence | MIT | MIT | BSD |

Two rows deserve emphasis. **Left recursion** is the dividing line between the two active libraries: grammars like `expr: expr "+" term | term` are natural to write and impossible to express directly in PyParsing's PEG model, which requires you to restructure into repetition. And **standalone export** is why Lark ends up in production systems that refuse runtime parser dependencies — it can emit a single Python file containing your compiled grammar.

## Decision Matrix

| Your task | Recommendation | Reason |
|---|---|---|
| New DSL or expression language | Lark | EBNF grammar is the deliverable; Earley handles ambiguity while you iterate |
| Query language for a product | Lark | LALR mode gives predictable performance once the grammar stabilises |
| Parsing vendor log lines | PyParsing | Build the grammar interactively, no compile step |
| Parsing `ifconfig` / `kubectl` output | PyParsing | Tolerant of format drift, easy to extend inline |
| Existing PLY grammar in production | PLY now, Lark next | Do not rewrite under deadline; do stop adding rules |
| Need a parser with zero runtime dependency | Lark standalone | Generates a self-contained parser module |
| Grammar with genuine ambiguity | Lark (Earley) | Ambiguity is handled and can be inspected |
| Quick field extraction, flat format | Regex | Cheaper than any parser library |

## Lark — Declarative Grammars With Two Engines

Lark's model is the familiar compiler-school one: you write a grammar, it builds a parse tree. What makes it pleasant in Python is that the grammar can live in a triple-quoted string next to the code that uses it, and the tree arrives already annotated.

Install and parse a greeting:

```bash
pip install lark
```

```python
from lark import Lark

parser = Lark(r"""
    start: WORD "," WORD "!"
    %import common.WORD
    %ignore " "
""")

tree = parser.parse("Hello, World!")
print(tree.pretty())
```

That is the entire README hello-world, and it demonstrates the two features that matter most in practice: `%import common.WORD` pulls terminals from a standard library of common patterns, and `%ignore " "` handles whitespace once instead of in every rule.

Real work usually needs the tree turned into data. Lark's `Transformer` walks the tree bottom-up and lets you replace nodes:

```python
from lark import Lark, Transformer

class Greeting(Transformer):
    def start(self, items):
        return {"salutation": str(items[0]), "addressee": str(items[2])}

parser = Lark(r"""
    start: WORD "," WORD "!"
    %import common.WORD
    %ignore " "
""", parser="lalr")

result = Greeting().transform(parser.parse("Hello, World!"))
print(result)   # {'salutation': 'Hello', 'addressee': 'World'}
```

The `parser="lalr"` argument is the performance switch. By default Lark uses Earley, which parses any context-free grammar including ambiguous and left-recursive ones, at the cost of higher complexity in bad cases. LALR is linear and much faster but rejects grammars with conflicts — you find out at construction time, not at 2 a.m. in production. The pragmatic workflow is to develop with Earley, get the grammar right, then try `parser="lalr"` and fix the conflicts it reports.

For deployment, Lark can compile the grammar ahead of time:

```bash
python -m lark.tools.standalone grammar.lark > my_parser.py
```

The generated module contains the parser tables and needs no `lark` import at runtime. If you ship a CLI or a lambda where dependency size is audited, this is the feature that decides the choice.

Grammar quality matters more than engine choice. Keep terminals narrow, prefer explicit `%ignore` over scattering `_WS` rules, and give ambiguous alternatives distinct prefixes. Most "Lark is slow" reports trace back to a grammar that forces Earley to explore exponentially many derivations because two rules can both match the same prefix.

## PyParsing — Grammars as Python Expressions

PyParsing predates the current enthusiasm for PEG and effectively popularised the style in Python: you compose parser objects with `+` for sequence, `|` for ordered choice, and `^` for longest-match choice. There is no grammar file and no compilation step, which makes it uniquely good for exploratory parsing.

```bash
pip install pyparsing
```

The canonical example, straight from the project README:

```python
from pyparsing import Word, alphas

greet = Word(alphas) + "," + Word(alphas) + "!"
print(greet.parse_string("Hello, World!"))
# ['Hello', ',', 'World', '!']
```

A more realistic task — parsing `key=value` pairs out of a config line — shows why people reach for it:

```python
import pyparsing as pp

key = pp.Word(pp.alphas + "_")
value = pp.QuotedString('"') | pp.Word(pp.printables, exclude_chars=",")
pair = pp.Group(key + pp.Suppress("=") + value).set_results_name("pair")

config = pp.Dict(pp.DelimitedList(pair))
result = config.parse_string('host="db.internal", port=5432')

print(result.as_dict())   # {'host': 'db.internal', 'port': '5432'}
```

Note the ordered choice in `value`: `QuotedString` is tried first, and only if it fails does PyParsing attempt the unquoted word. That ordering is the whole semantics of PEG — first match wins, no backtracking into a successful alternative. It is predictable once you internalise it, and a constant source of surprise when you do not.

Two performance controls are worth knowing. `pp.ParserElement.enable_packrat()` memoises intermediate results and can turn a pathological grammar from unusable into acceptable; it costs memory and is not always a win, so measure. And whitespace skipping is on by default, configurable globally through `pp.ParserElement.set_default_whitespace_chars()` — convenient until you parse a format where spaces are significant, at which point you turn it off per expression.

Where PyParsing falls down is left recursion. `expr = expr + "+" + term | term` will recurse forever, because PEG has no mechanism for it. You rewrite as `term + ZeroOrMore("+" + term)`, which is fine for flat expressions and increasingly awkward for real operator precedence. Once you find yourself hand-rolling precedence climbing around PyParsing, you have outgrown it.

## PLY — Still Running, No Longer Maintained

PLY is a faithful Python port of the lex/yacc pair, and for two decades it was the default answer for anyone who wanted a "real" parser in Python. It still works. The 3.11 release is stable, the LALR(1) algorithm is sound, and thousands of production tools embed it.

A minimal lexer looks like this:

```python
import ply.lex as lex

tokens = ("NUMBER", "PLUS")

t_PLUS = r"\+"
t_ignore = " \t"

def t_NUMBER(t):
    r"\d+"
    t.value = int(t.value)
    return t

def t_error(t):
    print(f"Illegal character {t.value[0]!r}")
    t.lexer.skip(1)

lexer = lex.lex()
lexer.input("3 + 4")
for tok in lexer:
    print(tok)
```

The grammar side uses rule functions whose docstrings *are* the production rules:

```python
import ply.yacc as yacc

def p_expr_plus(p):
    "expr : expr PLUS term"
    p[0] = p[1] + p[3]

parser = yacc.yacc()
print(parser.parse("3 + 4"))
```

That docstring-as-grammar trick is either elegant or horrifying depending on your taste, but it has a concrete engineering cost: your grammar is invisible to every tool that reads Python. Rename a function, reorder the file, or move a rule into another module, and you silently change the language you accept. PLY discovers rules by scanning the module namespace, which also means one lexer and one parser per module — an awkward constraint for libraries that want to expose a reusable grammar.

The abandonment notice changes the risk calculus rather than the technical merits. PLY has no dependencies and consists of essentially two files, so vendoring it is genuinely viable; Beazley himself suggests copying it into your project. But a parser library is exactly the kind of code that accumulates subtle bugs against new Python versions, and nobody is left to fix them. Treat PLY as frozen infrastructure: keep it if it works, add nothing to it, and budget a migration.

## Migrating Off PLY Without Rewriting Everything

The good news is that PLY grammars translate to Lark more directly than to PyParsing, because both are grammar-first tools with explicit terminals and productions. The mechanical steps:

1. **Inventory the tokens.** Every `t_NAME` variable or `t_NAME` function becomes a Lark terminal, usually a regex.
2. **Translate productions.** A PLY rule `expr : expr PLUS term` becomes `?expr: expr "+" term -> add | term` in Lark. Inline the operator token or keep it as a terminal depending on whether you need it in the tree.
3. **Move actions into a `Transformer`.** PLY mutates `p[0]` inside the rule; Lark returns a tree node and the transformer builds your objects. This is the part that takes time, because PLY rules often mix parsing and interpretation in the same function.
4. **Keep the old parser behind a flag until the outputs match.** Parse a corpus of real inputs with both implementations, serialise the results, and diff. Do not trust a handful of unit tests for a grammar migration.
5. **Retire the tables.** PLY writes `parser.out` and `parsetab.py` files; delete them from version control once the new parser is live.

If your PLY grammar is small — under a dozen productions — the migration is an afternoon. If it has grown precedence declarations and error recovery rules, expect a week and do it behind a feature flag.

## Pitfalls That Actually Bite

**LALR conflicts are a grammar design signal, not an error to silence.** Lark refusing to build an LALR parser usually means two alternatives share a prefix and your grammar is genuinely ambiguous there. Restructure instead of reaching for Earley everywhere; Earley will parse it, but you have moved the cost from build time to run time.

**`%ignore` is global.** In Lark, `%ignore WS` applies everywhere, including inside string literals if your terminators do not take priority. Lex string terminals before whitespace or you will spend an evening wondering why quoted values lose their spaces.

**PyParsing's ordered choice silently swallows alternatives.** `Keyword("select") | Keyword("select_all")` will match the prefix and leave `_all` unconsumed. Put longer alternatives first, or use `pp.MatchFirst` with explicit ordering in mind.

**Packrat parsing is not a universal speedup.** Memoisation costs memory proportional to input length times grammar positions. For short inputs the overhead exceeds the benefit. Benchmark before enabling it globally.

**A permissive grammar hides input bugs.** `Word(pp.printables)` accepts almost anything, so malformed data parses successfully into nonsense. Prefer narrow terminals and let the parser reject bad input loudly — that is the entire value of having a grammar.

**Parser tables regenerate on first run.** PLY's `yacc.yacc()` writes table files into the working directory unless configured otherwise, which breaks in read-only containers. Set `write_tables=False` explicitly if that is your deployment target — a fix you will only think of after the container fails.

## FAQ

### Is PLY still safe to use in 2026?

It is stable and dependency-free, and the author explicitly suggests vendoring it into your project. But it receives no maintenance, so no fix will arrive if a future Python release breaks it. For existing code the risk is manageable; for new code there is no reason to choose it over Lark.

### Should I use Earley or LALR in Lark?

Develop with Earley, ship with LALR if your grammar allows it. Earley accepts any context-free grammar, including ambiguous and left-recursive ones, but its worst-case complexity is much worse. LALR is linear and fast but requires a conflict-free grammar. Try `parser="lalr"` on every significant grammar change.

### Can PyParsing handle operator precedence?

Yes, through `pp.infix_notation()`, which builds the precedence ladder for you. What it cannot handle is direct left recursion in hand-written rules. For expression grammars with several precedence levels, `infix_notation` works well; for anything more exotic, Lark's EBNF is clearer.

### Which library is fastest?

For a well-formed LALR grammar, Lark's LALR mode is typically the fastest of the three, followed by PLY (also LALR) and then PyParsing. Real numbers depend entirely on grammar shape and input size, so benchmark with your own corpus — a parser that is fast on JSON and slow on your DSL is a common outcome.

### Can I distribute a parser without shipping the library?

With Lark, yes: `python -m lark.tools.standalone grammar.lark` emits a self-contained parser module. With PLY you vendor the two source files. PyParsing grammars are ordinary Python objects and cannot be precompiled, so the library must be installed wherever the grammar runs.

### How do I debug a grammar that will not parse?

In Lark, use `parser.parse(input, on_error=...)` or inspect `tree.pretty()` on a smaller input to find where the derivation diverges. In PyParsing, call `expr.set_debug()` and `expr.set_debug_actions()` to trace match attempts, and use `pp.ParserElement.verbose_stacktrace = True` when a rule fails inside an exception handler.

If you are choosing a parser generator rather than a hand-written grammar, our [lexer generator comparison](../2026-06-26-lexer-generator-tools-flex-re2c-ragel/) covers the tokenizer side of the same pipeline. For a different approach to the same problem — safe evaluation of expressions without a full grammar — see the [expression language comparison](../2026-09-27-expression-languages-cel-go-expr-lang-jsonata-starlark-comparison/). And when the input really is flat, the [regex engine comparison](../2026-06-22-regular-expression-engine-libraries-re2-pcre2-hyperscan-oniguruma/) explains which matcher to put behind your pattern.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Lark vs PyParsing vs PLY in 2026: Python Parser Libraries After PLY's Retirement",
  "description": "Comparison of Lark, PyParsing and PLY for Python parsing work in 2026, covering PLY's abandonment, LALR vs Earley trade-offs, working code and migration steps.",
  "datePublished": "2026-10-22",
  "dateModified": "2026-10-22",
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
