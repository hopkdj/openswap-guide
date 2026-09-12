---
title: "Rocq (Coq) vs Lean 4 vs Agda in 2026: Which Proof Assistant Should You Actually Learn?"
date: "2026-09-13"
draft: false
cover: "/img/screenshots/rocq-proof-script.jpg"
tags: ["formal-verification", "proof-assistants", "rocq", "lean4", "agda", "developer-tools"]
description: "A practical 2026 comparison of Rocq (formerly Coq), Lean 4 and Agda: real install commands, container images, CI setups, ecosystem size and a decision matrix for verified software, cryptography and mathematics."
---

Formal verification stopped being an academic exercise. The people who verify software now ship it: **CompCert's verified C compiler** runs in avionics toolchains, **seL4** is a verified microkernel, and industrial teams write machine-checked proofs for authorization languages, cryptographic primitives and protocol state machines. The question in 2026 is no longer "should we use a proof assistant?" but "which one?" — and the answer changes your build system, your library ecosystem and how painful your next upgrade will be.

Three proof assistants dominate open-source practice: **Rocq** (the prover formerly known as Coq, `coq/coq`, 5,572 GitHub stars, latest release V9.2.0), **Lean 4** (`leanprover/lean4`, 9,147 stars, v4.33.1) and **Agda** (`agda/agda`, 2,931 stars, v2.8.0.1). All three are free, all three are actively developed — and all three make you write proofs in a dependently typed language.

## TL;DR — Quick Verdict

**Choose Rocq** if you are verifying software or algorithms that must survive a decade: it has the deepest classical library ecosystem (`mathcomp`, `stdpp`, `Flocq`), the most mature proof automation ecosystem (`Ltac`, `SSReflect`, `Ltac2`), and industrial deployment history. **Choose Lean 4** if you want the fastest-moving toolchain, the richest mathematics library in the world (`mathlib4`, 4,111 stars and growing daily), and a functional programming language you can ship as an ordinary executable. **Choose Agda** if you care about proofs as *programs* — it is the cleanest environment for learning dependent types, has the most principled termination and coverage checking, and doubles as a executable programming language with excellent Haskell interoperability. For industrial verification, Rocq. For mathematics and momentum, Lean 4. For teaching and type theory, Agda.

## Proof Assistant Comparison Table

Live GitHub data, 13 September 2026.

| Prover | Stars | Latest release | Logic / foundation | Tactic automation | Main library | Build tool | Official container |
|---|---|---|---|---|---|---|---|
| **Rocq (Coq)** | 5,572 | V9.2.0 (2026-03-27) | Calculus of Inductive Constructions | Ltac, Ltac2, SSReflect, `lia`/`auto` | mathcomp, stdpp, Flocq, Coq-community | `dune`, `coq_makefile` | `coqorg/coq:8.20` |
| **Lean 4** | 9,147 | v4.33.1 (2026-08-21) | Dependent type theory (CIC-like, proof irrelevance) | `simp`, `omega`, `aesop`, `grind`, `<;>` combinators | mathlib4 (4,111★) | `lake` | `leanprovercommunity/lean:latest` |
| **Agda** | 2,931 | v2.8.0.1 (2026-08-31) | Martin-Löf type theory (intensional) | Limited: `Auto`, `RingSolver` | agda-stdlib | `cabal`, Emacs mode / LSP | None official |

The star gap does not mean Lean is "better" — it means Lean's community skews younger, more online and more concentrated in one repository. Rocq's strength is distributed across dozens of mature Coq-community projects that predate GitHub stars mattering.

## Decision Matrix: Pick by What You Are Proving

| Use case | Recommended prover | Why |
|---|---|---|
| Verifying C, assembly or compiler internals | **Rocq** | CompCert-grade tooling; mature VC generation and `Flocq` floating-point reasoning |
| Cryptographic proofs and protocol proofs | **Rocq** | `mathcomp` algebra hierarchy plus long-running verified crypto projects |
| Modern mathematics, research-level theorems | **Lean 4** | `mathlib4` is the largest formalised mathematics library available |
| Shipping executable verified code | **Lean 4** | Compiles to native binaries; usable as a general-purpose functional language |
| Learning dependent types and type theory | **Agda** | Cleanest syntax, most readable error messages, most principled checker |
| Haskell-adjacent workflows | **Agda** | Direct Haskell FFI and cabal-based packaging |
| Large proof codebases you will maintain for years | **Rocq** | Conservative language evolution, backward-compatible releases |
| Fast-moving research with continuous library updates | **Lean 4** | Weekly releases; toolchain versioned per project via `lakefile` |

## Rocq (Coq) — The Industrial Standard

Rocq is a rename of Coq with a V9 release line and a reengineered kernel, but the ecosystem and proof language are continuous with the Coq you have seen in papers for two decades. That continuity is the selling point: your proofs from five years ago still compile, and the standard library stack (`mathcomp`, `stdpp`, `Flocq`, `CompCert`) has no equivalent breadth anywhere else.

![Rocq proof script with goals visible in the interactive prover](/img/screenshots/rocq-proof-script.jpg "An interactive proof script in the Rocq Prover")

**Install it with opam** (the recommended path for a specific V9 line):

```bash
opam init --bare -y
opam switch create rocq 5.2.0
eval $(opam env)
opam install -y rocq-core
```

**Or use the maintained container image for CI and isolated work:**

```yaml
services:
  rocq:
    image: coqorg/coq:8.20
    container_name: rocq-prover
    working_dir: /work
    volumes:
      - ./proofs:/work:rw
      - rocq-opam:/home/coq/.opam
    command: ["coqc", "-Q", "/work", "MyLib", "/work/theories/VerifiedParser.v"]

volumes:
  rocq-opam:
```

**A small verified function with a real proof obligation:**

```coq
From Coq Require Import Arith List.
Import ListNotations.

Fixpoint insert (x : nat) (l : list nat) : list nat :=
  match l with
  | [] => [x]
  | y :: tl => if x <=? y then x :: l else y :: insert x tl
  end.

Fixpoint isort (l : list nat) : list nat :=
  match l with
  | [] => []
  | h :: t => insert h (isort t)
  end.

Lemma insert_length : forall x l, length (insert x l) = S (length l).
Proof.
  intros x l; induction l as [| y tl IH]; simpl.
  - reflexivity.
  - destruct (x <=? y); simpl; [reflexivity | rewrite IH; reflexivity].
Qed.

Lemma isort_length : forall l, length (isort l) = length l.
Proof.
  induction l as [| h t IH]; simpl.
  - reflexivity.
  - rewrite insert_length, IH; reflexivity.
Qed.
```

**Where it wins:** tooling maturity, library depth, and a language that changes slowly enough to build a decade-long codebase on. **Where it costs you:** Ltac is famously hard to debug, and the tactic-language churn between Ltac, SSReflect and Ltac2 means teams standardise on one style and stay there.

## Lean 4 — The Fastest-Moving Prover

Lean 4 is both a proof assistant and a general-purpose functional programming language, with a self-hosted compiler that produces native binaries. Since the release of Lean 4 the project has attracted an extraordinary amount of industrial and academic participation: the official project pages showcase verified authorization engines, Rust verification toolchains, cryptographic libraries and mathematical formalisation at research scale.

![Lean 4 project banner from the official site](/img/screenshots/lean4-banner.jpg "Lean 4, the dependently typed prover and programming language")

**Install with elan** (the official toolchain manager — it pins the Lean version per project, which keeps mathlib-based work reproducible):

```bash
curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | sh -s -- -y
source "$HOME/.elan/env"
lean --version
```

**Start a project and add the mathematics library:**

```bash
lake new verified_scheduler
cd verified_scheduler
# edit lakefile.toml to require mathlib, then:
lake update
lake exe cache get      # downloads prebuilt mathlib artifacts instead of recompiling
lake build
```

```lean
import Mathlib.Data.Nat.Basic

theorem add_comm_example (m n : Nat) : m + n = n + m := by
  omega

theorem sum_first_n (n : Nat) : 2 * (Finset.range (n + 1)).sum id = n * (n + 1) := by
  induction n with
  | zero => simp
  | succ k ih =>
    rw [Finset.sum_range_succ]
    omega
```

**Container-based CI:**

```yaml
services:
  lean:
    image: leanprovercommunity/lean:latest
    working_dir: /work
    volumes:
      - ./:/work
    command: ["bash", "-lc", "lake exe cache get && lake build"]
```

**Where it wins:** momentum. Tactic automation (`simp`, `omega`, `aesop`, `grind`) is genuinely usable, `mathlib4` covers mathematics that no other library approaches, and the language is pleasant enough to use for ordinary programs. **Where it costs you:** `mathlib4` moves fast enough that dependency breakage is a routine part of maintenance — you must pin toolchain versions in the `lakefile` and expect to spend real time on upgrades each year.

## Agda — Proofs as Programs

Agda implements Martin-Löf type theory with a famously principled checker: **all functions must be structurally terminating and all pattern matches exhaustive**, and the errors it produces when they are not are the clearest in the field. That strictness makes Agda the best environment for learning dependent types, and a surprisingly practical language for writing verified small tools.

**Install via cabal or a distribution package:**

```bash
# From Hackage (pinned version)
cabal update && cabal install Agda-2.8.0.1

# Debian/Ubuntu
sudo apt install agda agda-stdlib

# Editor/IDE integration (Emacs mode is the classic; there is a language server too)
agda --version
```

**A verified total function with a proof of a real property:**

```agda
open import Data.Nat
open import Data.List using (List; []; _∷_; length)
open import Relation.Binary.PropositionalEquality using (_≡_; refl; cong)

-- insert into a sorted list; Agda checks totality for us
insert : ℕ → List ℕ → List ℕ
insert x []       = x ∷ []
insert x (y ∷ ys) with x ≤? y
... | yes _ = x ∷ y ∷ ys
... | no  _ = y ∷ insert x ys

-- The type checker requires that this recursion terminates.
-- If the recursive call were not structurally smaller, this would not compile.
insert-length : (x : ℕ) (xs : List ℕ) → length (insert x xs) ≡ suc (length xs)
insert-length x []       = refl
insert-length x (y ∷ ys) with x ≤? y
... | yes _ = refl
... | no  _ = cong suc (insert-length x ys)
```

**Where it wins:** the type system is the documentation, termination checking is not negotiable, and the syntax is the most readable of the three. **Where it costs you:** the ecosystem is small, there is no official container image, tactic support is minimal, and large developments require more manual proof engineering than Rocq or Lean.

## Running Proofs in CI (and What It Actually Costs)

Proof checking is CPU-heavy and reproducible, which makes it a perfect CI job — and a bad candidate for compiling on every push if you can avoid it.

| Strategy | Rocq | Lean 4 | Agda |
|---|---|---|---|
| Cache compiled artifacts | `dune`/`coq_makefile` `.vo` files | `lake exe cache get` (mathlib) | cabal store + `.agdai` files |
| Typical first-build cost | Minutes for a mid-size development | Minutes without cache, hours with full mathlib from source | Minutes to tens of minutes |
| Reproducibility lever | Pin opam switch + image tag | Pin toolchain in `lean-toolchain` | Pin Agda version + stdlib commit |

```yaml
# A CI job that fails the build when a proof stops checking
name: verify
on: [push]
jobs:
  proofs:
    runs-on: ubuntu-latest
    container: coqorg/coq:8.20
    steps:
      - uses: actions/checkout@v4
      - name: Check all proofs
        run: make -C theories   # your coq_makefile/dune target
```

If you are exploring automated reasoning that does *not* require interactive proofs, our [SMT solver comparison](../2026-06-22-smt-solver-libraries-z3-cvc5-yices-boolector-bitwuzla/) covers the solver-first approach, and the [constraint programming solver roundup](../2026-06-22-constraint-programming-solvers-ortools-gecode-choco-minizinc-chuffed/) covers search-based modelling. For the tooling side of compiler-oriented work, see the [Compiler Explorer guide](../2026-06-18-self-hosted-compiler-explorer-godbolt-code-analysis/).

## Pitfalls and Migration Traps

- **Pin your toolchain or your proofs will rot.** `mathlib4` and Lean move fast; Rocq and Agda move slowly but do break compatibility at major versions. Always commit `lean-toolchain`, an opam switch file, or an exact Agda version.
- **`Prop` versus `Bool` is not a style choice.** Mixing computational booleans with propositions is the most common beginner trap and produces goals that `omega` or `lia` cannot close. Decide early and keep proofs on the propositional side.
- **Termination checking will reject your natural formulation.** Agda and Lean require structural recursion or an explicit well-founded measure. Rewriting a function to satisfy the checker often produces *better* code — but budget time for it.
- **Universe polymorphism bites late.** Both Rocq and Agda make you manage universe levels. Problems usually appear when a definition that worked at one level gets reused at another, deep inside a finished development.
- **Never trust a proof you have not re-checked in CI.** `Admitted`, `postulate`, and `sorry` are silent holes. Grep for them in the pipeline and fail the build if they appear in a release branch.
- **Container images lag releases.** The maintained Rocq image tracked the 8.20 line while the Rocq releases had already moved to V9.2.0 — for the newest kernel, install via opam rather than relying on the container tag.
- **Do not benchmark proof assistants on runtime.** The metric that matters is *time to a checked proof*: how quickly a team can state a theorem and get automation to close the routine parts.

## FAQ

**What is the difference between Rocq and Coq?**
Rocq is the new name of the Coq proof assistant, with a V9 release line and a modernised kernel. The proof language, libraries and community remain continuous, which is why you still see `coq` everywhere in tooling names, Docker tags and package managers.

**Is Lean 4 better than Coq for mathematics?**
For contemporary research mathematics, Lean 4 currently has the stronger story because `mathlib4` is the largest single formalised mathematics library and is updated continuously. For verified software, cryptography and long-lived industrial proof codebases, Rocq's mature library stack and conservative evolution are usually the better fit.

**Which proof assistant is easiest to learn?**
Agda, for the type theory itself — its syntax, error messages and termination checking are the clearest of the three. Lean 4, for getting to a useful result quickly, because `simp`, `omega` and `aesop` close a large fraction of routine goals automatically.

**Do I need a proof assistant to use formal methods?**
No. If your problem is "is this configuration or constraint system satisfiable", an SMT solver or constraint solver will be faster to adopt. Proof assistants are for statements you need to be *certain* about for the life of the software — correctness of a compiler pass, a cryptographic primitive, a protocol invariant.

**Can I run proofs in Docker or Kubernetes?**
Yes. `coqorg/coq:8.20` and `leanprovercommunity/lean:latest` are maintained images, and Agda builds fine from a Haskell-based image. Cache compiled artifacts in a volume — proof checking is CPU-bound and re-checking everything on each run wastes minutes per build.

**How big are real verified developments?**
Large: verified compilers and microkernels are multi-year, multi-person projects measured in hundreds of thousands of lines of proof. But you do not need that scale to benefit — a few hundred lines proving the invariant of a critical function is already a good return on investment.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rocq (Coq) vs Lean 4 vs Agda in 2026: Which Proof Assistant Should You Actually Learn?",
  "description": "A practical 2026 comparison of Rocq (formerly Coq), Lean 4 and Agda with real install commands, Docker and CI configurations, live release data, library ecosystems and a decision matrix for verified software and mathematics.",
  "datePublished": "2026-09-13",
  "dateModified": "2026-09-13",
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
