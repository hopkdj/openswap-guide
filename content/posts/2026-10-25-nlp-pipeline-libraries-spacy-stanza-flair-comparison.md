---
title: "spaCy vs Stanza vs Flair in 2026: Which NLP Pipeline Should You Actually Ship?"
date: "2026-10-25"
tags: ["nlp", "python", "developer-tools", "text-processing", "data-pipelines"]
draft: false
cover: "/img/screenshots/spacy-displacy.jpg"
---

You have 4 million support tickets, 900 PDFs of contracts, and a deadline. You need entities, lemmas, and dependency parses — not a research project. The wrong library choice costs you weeks: one team shipped a pipeline that needed 61 GB of RAM to process a 200 MB corpus, another discovered their tokenizer split German compound words into four useless fragments after go-live.

The three libraries that actually get used for this work are **spaCy** (33,990★, last push 2026-10-23), **Stanza** (7,903★, 2026-10-23), and **Flair** (14,395★, 2026-10-19). They are not interchangeable. Below is the honest split, with real install commands, real API calls, and the traps nobody puts in the README.

## TL;DR: The 30-Second Verdict

- **Ship spaCy** if you need speed, a stable API, and a pipeline that runs on a $12/month VPS. It is the only one of the three built like production software first and research code second.
- **Ship Stanza** if your corpus is not English. Its 70+ language coverage and CoreNLP-compatible linguistic output beat both alternatives for morphologically rich languages.
- **Ship Flair** only if accuracy on a specific benchmark is the business requirement and you have GPU budget. Expect 5-15x the memory of spaCy for single-digit accuracy gains on in-domain text.
- **Do not mix all three** in one service. You will ship three copies of PyTorch, three tokenization conventions, and offset bugs you will debug for a month.

## How These Three Actually Differ

All three do tokenization, part-of-speech tagging, lemmatization, dependency parsing, and named entity recognition. The difference is what they optimize for.

spaCy is a **compiled pipeline**: pipeline components are arranged in a fixed `nlp` object, models ship as small wheel files, and inference runs through thinc on CPU efficiently. Stanza is a **PyTorch neural pipeline** built by the Stanford NLP group, wrapping models trained per language with a CoreNLP-compatible data model. Flair is a **research framework** — sequences of embeddings stacked into taggers, with the contextual string embedding trick that made it famous in 2018 and a broad model hub today.

That architectural split predicts almost every practical difference you will hit: install size, cold-start latency, how you customize the pipeline, and how painful upgrades are.

## Quick Comparison Table

| Dimension | spaCy | Stanza | Flair |
|---|---|---|---|
| **GitHub stars** | 33,990 | 7,903 | 14,395 |
| **Last commit (2026)** | 2026-10-23 | 2026-10-23 | 2026-10-19 |
| **License** | MIT | Apache-2.0 | MIT |
| **Runtime** | thinc / numpy (CPU-first) | PyTorch | PyTorch |
| **Languages** | ~25 trained pipelines | 70+ languages | Model-dependent, strong on ~12 |
| **Default install size** | ~50 MB + model wheels | ~2.5 GB (torch) | ~2.5 GB (torch) |
| **CPU throughput (short docs)** | Very high (10k+ docs/s on 8 cores) | Moderate | Low |
| **GPU required for sane speed** | No | Recommended for bulk | Effectively yes |
| **Custom training** | `spacy train` config system | Python training loop | Python training loop |
| **Rule-based additions** | `EntityRuler`, `Matcher` | Limited | Limited |
| **Best fit** | Production services | Multilingual corpora | Benchmark-chasing |

The install-size row matters more than the star counts. On a 2 GB container, `pip install flair` fails outright — PyTorch plus model weights do not fit.

## Decision Matrix: Pick By Use Case

| Your situation | Pick | Why |
|---|---|---|
| REST service that must answer in <100 ms | **spaCy** | No torch import, models load in ~1 s, predictable per-request cost |
| 40-language crawl of product reviews | **Stanza** | One `Pipeline(lang=...)` per language, consistent Universal Dependencies output |
| Entity extraction on legal or biomedical text where recall is revenue | **Flair** | Stacked embeddings still win on domain-specific NER |
| Air-gapped server, no GPU, 4 GB RAM | **spaCy** | Only realistic option of the three |
| You need dependency trees plus CoreNLP-style semantics | **Stanza** | Designed as a CoreNLP successor with matching annotations |
| Research notebook exploring embedding stacks | **Flair** | Fastest path from idea to a trained tagger |
| Mixed workload: 95% English, 5% everything else | **spaCy + Stanza fallback** | Route by detected language; keep torch out of the hot path |

## spaCy — The Production Workhorse

![spaCy displaCy dependency visualization running in a notebook](/img/screenshots/spacy-displacy.jpg "spaCy displaCy rendering a dependency parse and named entities")

spaCy's selling point is that the boring parts are solved. Model download is one command, the pipeline object is serializable, and the same code runs on your laptop and in a container.

```bash
python3 -m venv /opt/nlp && source /opt/nlp/bin/activate
pip install -U "spacy>=3.7,<4"
python -m spacy download en_core_web_sm
python -m spacy validate
```

```python
import spacy

nlp = spacy.load("en_core_web_sm")          # swap for _md/_lg/_trf for accuracy
nlp.add_pipe("entity_ruler", before="ner", config={
    "phrase_matcher_attr": "LOWER",
    "overwrite_ents": True,
    "patterns": [
        {"label": "PRODUCT", "pattern": "openswap guide"},
        {"label": "PRODUCT", "pattern": [{"LOWER": "pistack"}, {"LOWER": "."}, {"LOWER": "xyz"}]},
    ],
})

docs = nlp.pipe(open("tickets.txt").read().splitlines(), batch_size=256, n_process=4)
for doc in docs:
    for ent in doc.ents:
        print(ent.label_, ent.text, ent.start_char, ent.end_char)
```

Three things worth knowing. First, `nlp.pipe` with `n_process>1` is the difference between 900 docs/s and 9,000 docs/s — naive per-document calls leave most of the machine idle. Second, `entity_ruler` before `ner` with `overwrite_ents=True` is how you fix domain vocabulary without retraining anything; this alone fixes most "our product names are tagged as ORG" complaints. Third, the `_trf` pipelines import a transformer stack and lose the CPU advantage — if you reach for them, benchmark against Stanza before committing.

**Where spaCy fails you:** non-English coverage drops off a cliff outside its trained pipelines, and its NER is trained for general-purpose text. On dense biomedical or legal strings it misses entities that Stanza and Flair catch. It also has no built-in sentence-level sentiment model worth using; you will bolt on your own classifier.

## Stanza — The Multilingual Default

Stanza exists because the Stanford team wanted CoreNLP's linguistic rigor without Java. Every annotation is a typed object, and the same `Pipeline` API works across 70+ languages with Universal Dependencies labels.

```bash
pip install -U stanza
python -c "import stanza; stanza.download('de'); stanza.download('zh-hans')"
```

```python
import stanza

nlp = stanza.Pipeline(
    lang="de",
    processors="tokenize,mwt,pos,lemma,depparse,ner",
    tokenize_pretokenized=False,
    use_gpu=False,
    verbose=False,
)

doc = nlp("Die Bundesnetzagentur prüfte den Netzausbau in Baden-Württemberg.")
for sent in doc.sentences:
    for word in sent.words:
        print(f"{word.id}\t{word.text}\t{word.lemma}\t{word.upos}\t{word.head}\t{word.deprel}")
    for ent in sent.ents:
        print("ENT:", ent.text, ent.type)
```

The `mwt` processor (multi-word tokens) is the detail that makes Stanza worth its weight for German, Czech, or Hindi: it expands contractions and clitics into syntactic words with proper IDs, so your dependency arcs line up with the grammar instead of the surface string. spaCy's tokenizer handles these languages, but you get surface tokens, not linguistic words.

**Where Stanza fails you:** throughput. Loading a pipeline per language costs 1-3 GB of RSS, and batch inference on CPU is roughly an order of magnitude slower than spaCy for short documents. In a request/response service, cold starts are painful. It is a batch tool: run it in a worker, write annotations to a store, and never call it inline in a web handler.

If you want the CoreNLP server semantics without Python, Stanza also ships a client for a Java CoreNLP server — useful when a linguistics team already owns a CoreNLP deployment.

## Flair — The Accuracy Maximalist

Flair's pitch is simple: stack embeddings, let the tagger learn, accept the cost. Its contextual string embeddings were designed for sequence labeling, and the model hub includes taggers that remain competitive on standard NER benchmarks.

```bash
pip install -U flair
```

```python
from flair.data import Sentence
from flair.models import SequenceTagger
from flair.embeddings import WordEmbeddings, FlairEmbeddings, DocumentRNNEmbeddings

tagger = SequenceTagger.load("flair/ner-english-large")
sentence = Sentence("The Bundesnetzagentur fined the operator in Baden-Württemberg.")
tagger.predict(sentence)

for entity in sentence.get_spans("ner"):
    print(entity.text, entity.tag, round(entity.score, 4))

# Stacked embeddings for a custom tagger
embeddings = DocumentRNNEmbeddings([
    WordEmbeddings("glove"),
    FlairEmbeddings("news-forward-fast"),
    FlairEmbeddings("news-backward-fast"),
])
```

Two practical notes. First, `flair/ner-english-large` downloads several hundred megabytes on first use — pre-bake it into your image or your first request times out. Second, the embedding stack is where the accuracy comes from and also where the memory goes: three embedding layers plus a BiLSTM tagger is why people report 4-8 GB RSS for what spaCy does in 400 MB.

**Where Flair fails you:** latency under 100 ms per document is not happening on CPU, and the API surface changes more often than spaCy's. Pin exact versions in production. Also be honest about the benchmark gap: published CoNLL-2003 numbers put the strongest Flair and Stanza configurations in the low 90s F1, while spaCy's CNN pipelines historically trail by several points. On your own domain, that gap can invert entirely — the only valid test is 500 hand-labeled examples from your corpus.

## Pitfalls and Migration Traps

**Tokenization is not portable.** Offsets from spaCy (`start_char`, `end_char`) do not match Stanza's `start_char`/`end_char` on the same text when contractions or multi-word tokens are involved. If you migrate, re-annotate rather than reusing stored offsets — mismatched offsets produce silently wrong highlight spans in UIs.

**Sentence splitting changes entity boundaries.** Flair tags per `Sentence`, spaCy per `Doc`. Feed Flair a 30,000-character document as one sentence and your tagger's context window will truncate. Always split first.

**Model licenses differ from code licenses.** The libraries are MIT or Apache-2.0, but individual pretrained checkpoints can carry different terms. Audit the model, not just the repo.

**Version pinning is not optional with torch.** `pip install flair` today and in three months can resolve different torch builds. Pin torch, torchaudio, and the library together in a lockfile, or your container will build fine on Monday and fail on the GPU node on Friday.

**Do not run two of these in one process.** Importing spaCy and Flair together doubles native memory and can deadlock thread pools under gunicorn preload. Use separate workers behind a queue.

**Lemma casing bites.** spaCy preserves case in lemmas for proper nouns; Stanza's `word.lemma` can be `None` for unknown tokens. Defensive code (`lemma or word.text`) saves you a `TypeError` in production.

## Performance and Memory Reality Check

Measure before you commit. A realistic comparison on 8 vCPU, 16 GB RAM, 20,000 short English tickets (under 60 words each) looks like this in practice:

| Metric | spaCy `en_core_web_sm` | Stanza (en, all processors) | Flair `ner-english-large` |
|---|---|---|---|
| Throughput | ~6,000-9,000 docs/s (4 procs) | ~80-150 docs/s | ~25-60 docs/s |
| RSS after load | 350-500 MB | 2.5-3.5 GB | 4-6 GB |
| Cold start | <2 s | 15-45 s | 20-60 s |
| GPU helps? | Marginally | Yes, 3-8x | Yes, 5-10x |

The lesson: pick the cheapest model that clears your accuracy bar, then spend the saved compute on more labeled data. Teams routinely burn a GPU budget chasing two F1 points that 300 additional annotations would have delivered.

## FAQ

**Which of the three is fastest on CPU?**
spaCy, by a wide margin — typically 50-100x the throughput of Flair and 40-80x that of a full Stanza pipeline on short English documents. The gap narrows on GPU but never closes.

**Can I use spaCy for non-English text?**
Yes for roughly 25 languages with trained pipelines, but coverage and quality vary. For low-resource or morphologically rich languages, Stanza's per-language models and Universal Dependencies output are the safer default.

**Does Flair still make sense in 2026?**
For domain-specific sequence labeling where you can fine-tune and you have GPU capacity, yes. For general-purpose English at scale, spaCy's accuracy is close enough that the operational cost of torch rarely pays for itself.

**How do I get custom entity types without retraining?**
spaCy: `EntityRuler` with `overwrite_ents=True` placed before `ner`. Stanza: post-process with a gazetteer, or train a new model. Flair: train a `SequenceTagger` on a few hundred annotated sentences — it learns quickly from small data.

**Which handles dependency parsing best?**
Stanza produces CoreNLP-compatible Universal Dependencies and handles multi-word tokens explicitly, so it is the strongest choice for linguistic analysis. spaCy's parser is faster and good enough for relation extraction heuristics.

**Can these run fully offline?**
All three can, but you must pre-download models. spaCy: `python -m spacy download` on a networked host, then copy the wheel. Stanza: `stanza.download()` then set `DOWNLOAD_DIR` or point `Pipeline(dir=...)` at the cached resources. Flair: cache the `flair/` model directory into your image.

**What about memory on small VPS instances?**
Only spaCy is realistic under 1 GB. If you must run Stanza or Flair on a small box, move inference to a batch worker and keep the web tier dependency-free.

For a broader look at self-hosted text analysis platforms that wrap these libraries, see our [Voyant vs GATE vs Apache UIMA comparison](../2026-06-15-text-mining-platforms-voyant-gate-uima/). If your pipeline output feeds a redaction workflow, our [Presidio vs scrubadub vs ARX guide](../self-hosted-pii-detection-anonymization-presidio-scrubadub-arx-2026/) covers the anonymization layer. And for contract-heavy corpora, the [legal document intelligence comparison](../2026-06-18-self-hosted-legal-document-intelligence-opencontracts-docassemble-doclense/) shows where entity extraction actually pays off.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "spaCy vs Stanza vs Flair in 2026: Which NLP Pipeline Should You Actually Ship?",
  "description": "A practical 2026 comparison of spaCy, Stanza, and Flair for production text pipelines: throughput, memory, language coverage, real code, and migration traps.",
  "datePublished": "2026-10-25",
  "dateModified": "2026-10-25",
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
