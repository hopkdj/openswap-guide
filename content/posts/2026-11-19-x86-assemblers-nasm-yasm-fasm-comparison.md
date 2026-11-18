---
title: "NASM vs YASM vs FASM in 2026: Which x86 Assembler Should You Actually Use?"
date: "2026-11-19"
tags: ["assembly", "developer-tools", "compilers", "low-level", "build-tools"]
draft: false
cover: "/img/screenshots/nasm-official.jpg"
description: "A hands-on comparison of NASM, YASM and FASM in 2026: syntax, output formats, macro systems, maintenance status, real build commands and the pitfalls that bite when you ship assembly."
---

You need an assembler for exactly one reason: something in your build has to touch the metal. A bootloader, a hand-tuned crypto inner loop, a 400-byte binary for an embedded target, a retro demo that has to fit in a fixed memory map. At that point your compiler's integrated assembler stops being convenient and you start caring about macro systems, output formats, and whether the project is still alive.

The problem is that the internet's advice on this topic is frozen around 2012. YASM was the hot new thing, NASM was "the standard", and FASM was the weird one that produced impossibly small executables. Two of those statements have aged badly. Here is what the three toolchains actually look like when you build with them today.

## TL;DR: the 30-second verdict

- **Use NASM** for anything new on Linux, Windows, or bare metal x86. It has the most complete instruction coverage, the most predictable macro preprocessor, and it is actively maintained.
- **Use YASM only if you inherit a build that already depends on it**, or you genuinely need its dual NASM/GAS parser. Its last tagged release is from 2014, and you will hit missing instruction encodings on modern vector extensions.
- **Use FASM when binary size or self-hosting is the point.** It is the only one of the three that assembles and links in a single pass with no external linker, on every major OS, and it assembles its own source code.

If you only skim one paragraph: NASM is the default, FASM is the specialist tool, YASM is legacy maintenance.

## Side-by-side comparison

| Dimension | NASM | YASM | FASM |
|---|---|---|---|
| GitHub stars | **3,365** | 1,487 | no GitHub repo (flatassembler.net) |
| Last upstream activity | **2026-08-19** | 2026-08-01 (branch commits) | active 1.73.x series |
| Last tagged release | 3.x series, regular | 1.3.0 (2014) | 1.73.x |
| License | BSD-2-Clause | BSD (new) + other | BSD-style, source included |
| Input syntax | Intel-style, NASM dialect | NASM **and** GAS dialects | FASM dialect (Intel-like) |
| Output formats | bin, elf32/64, win32/64, macho32/64, coff, rdf, aout | bin, elf32/64, win32/64, macho32/64, coff, rdoff2 | bin, elf/elf64, PE, COFF, Mach-O, MZ |
| Macro system | multi-line `%macro`, context stack | NASM-compatible | powerful `macro` with local labels |
| Needs external linker | yes (except `-f bin`) | yes (except `-f bin`) | **no** for flat formats |
| Debug info | DWARF, CodeView | DWARF 2, STABS, CodeView 8 | limited (`.fas` / symbol dump) |
| Best fit | general x86 work | legacy builds, GAS syntax needs | tiny binaries, OS dev, Windows |

Two numbers matter more than the rest. NASM's repository is pushed to weekly; YASM's releases stopped twelve years ago even though the tree still receives occasional commits. FASM has no GitHub presence at all and does not need one — it ships as a self-contained binary that compiles itself.

## Scenario decision matrix

| Your situation | Pick | Why |
|---|---|---|
| New Linux kernel module, bootloader, or freestanding code | **NASM** | ELF64 output is battle-tested, DWARF works with `gdb`, macro layer is predictable |
| Existing project with `yasm` in its Makefile | **YASM** (for now) | NASM is 95% source-compatible, but test before you swap |
| You must fit a payload into a few hundred bytes | **FASM** | Single-pass assembly, no linker padding, tight section control |
| Windows shellcode or PE stub | **FASM** | Direct PE/MZ output, no COFF round-trip |
| You have GAS-syntax sources you refuse to rewrite | **YASM** | `-p gas` parses AT&T syntax |
| Teaching or writing portable examples | **NASM** | Most tutorials, Stack Overflow answers and textbooks target it |
| Cross-compiling for aarch64/riscv | none of these | use the target's GNU or LLVM toolchain |

## NASM: the default for a reason

NASM ("Netwide Assembler") earns its position by being boring in the right ways. The preprocessor is a real macro processor rather than a text substitution hack, output formats are selected with a single `-f` flag, and the diagnostics point at the offending line instead of an internal token index.

A minimal freestanding Linux x86-64 program:

```nasm
; hello.asm — NASM, Linux x86-64, no libc
section .data
    msg db "hello, assembler", 10
    len equ $ - msg

section .text
    global _start
_start:
    mov rax, 1          ; sys_write
    mov rdi, 1          ; stdout
    mov rsi, msg
    mov rdx, len
    syscall

    mov rax, 60         ; sys_exit
    xor rdi, rdi
    syscall

section .note.GNU-stack noalloc noexec nowrite progbits
```

Build and verify it:

```bash
nasm -f elf64 -g -F dwarf -Wall hello.asm -o hello.o
ld -o hello hello.o
./hello
file hello          # ELF 64-bit LSB executable, statically linked
objdump -d hello    # confirm the encoding you expected
```

That last `section .note.GNU-stack` line is not decoration. Without it, modern binutils marks the stack executable and you get a warning that turns into a hard error under `-z noexecstack` defaults.

The macro layer is where NASM pulls ahead for real work. Multi-line macros with local labels, conditional assembly, and repetition are all first-class:

```nasm
%macro prologue 1
    push rbp
    mov rbp, rsp
    sub rsp, %1
%endmacro

%macro syscall3 4
    mov rax, %1
    mov rdi, %2
    mov rsi, %3
    mov rdx, %4
    syscall
%endmacro
```

A Makefile that keeps debug info usable but still produces a static binary:

```make
ASM      := nasm
ASMFLAGS := -f elf64 -g -F dwarf -Wall -Ox
LDFLAGS  := -static -nostdlib

hello: hello.o
	ld $(LDFLAGS) -o $@ $<

hello.o: hello.asm
	$(ASM) $(ASMFLAGS) -o $@ $<

clean:
	rm -f hello hello.o
.PHONY: clean
```

For position-independent code the one flag people forget is `default rel`, which makes RIP-relative addressing the default so your data references survive linking into a shared object or a PIE:

```nasm
default rel
lea rsi, [msg]      ; RIP-relative, not absolute
```

NASM also emits raw binaries with `-f bin`, which is how most hobby bootloaders are built:

```bash
nasm -f bin boot.asm -o boot.bin      # exactly the bytes in the file, no ELF wrapper
```

## YASM: still useful, no longer growing

YASM began as a clean-room rewrite of NASM and its README still advertises the real differentiator: it accepts both NASM and GAS syntax, and it emits binary, ELF32/64, Mach-O 32/64, RDOFF2, COFF, Win32 and Win64 objects, with STABS, DWARF 2 and CodeView 8 debug info. If you have a mixed codebase where half the `.s` files are AT&T syntax, YASM can assemble both without a second toolchain:

```bash
yasm -p nasm -f elf64 -g dwarf2 hello.asm -o hello.o   # NASM dialect
yasm -p gas  -f elf64 -g dwarf2 att_source.s -o att.o  # AT&T dialect
ld -o hello hello.o
```

It also has a preprocessing story NASM lacks: `-r cpp` runs the C preprocessor over your source, which some projects use to share constants with C headers.

```bash
yasm -r cpp -p nasm -f elf64 -I include/ module.asm -o module.o
```

The catch is maintenance. YASM 1.3.0 shipped in 2014. The tree still gets commits, but the release cadence is effectively zero, and modern instruction sets are where that hurts. AVX-512 subsets, APX, and the newest CET/shadow-stack encodings are either missing or incomplete. You find out at assemble time with an "unrecognized instruction" error, or worse, at runtime with an encoding that is subtly wrong.

If you are migrating a YASM build to NASM, the realistic checklist is: drop `-p gas` (rewrite AT&T files or keep YASM for those), replace `-r cpp` with NASM's `%include` plus `-D` defines, and re-verify every `-g dwarf2` debug path because the DWARF producers differ. Most NASM-dialect sources assemble unchanged.

## FASM: the size specialist

FASM ("flat assembler") is the one that surprises people. It is written in itself, distributed as source plus prebuilt binaries for DOS, Windows, Linux and Unix derivatives, and it does assembly and linking in a single pass. For flat binary formats there is no linker step at all.

```fasm
; hello.asm — FASM, Linux x86-64 ELF executable
format ELF64 executable 3

segment readable executable
entry start
start:
    mov eax, 1              ; sys_write
    mov edi, 1              ; stdout
    lea rsi, [msg]
    mov edx, msg_len
    syscall

    mov eax, 60             ; sys_exit
    xor edi, edi
    syscall

segment readable writeable
msg db 'hello, assembler', 10
msg_len = $ - msg
```

```bash
fasm hello.asm hello
chmod +x hello
./hello
```

No `ld`, no `objcopy`, no linker script. That single-pass design is why FASM output tends to be smaller: there is no alignment padding or section merging imposed by a linker, and `org` gives you absolute control over the load address in `format binary` mode.

```fasm
format binary
org 0x7C00          ; classic MBR load address
```

Its macro system is at least as capable as NASM's, with local labels inside macros that do not leak:

```fasm
macro push_all {
    push rax rbx rcx rdx
}

macro sys_call nr*, a1*, a2*, a3* {
    mov eax, nr
    mov edi, a1
    mov rsi, a2
    mov edx, a3
    syscall
}
```

The trade-offs are real. Debug info support is thin compared with NASM's DWARF output, so single-stepping through FASM-produced code with `gdb` gives you symbols at best, not line numbers. The dialect is FASM-specific: `segment` instead of `section`, `entry` instead of `global _start`, `db` strings with single quotes. Porting NASM source to FASM is a mechanical but non-trivial rewrite, and there is no GAS parser.

It also has no GitHub repository, which trips up supply-chain tooling that expects one. Distribution is the project's own site plus distro packages (`fasm` in Debian/Ubuntu, `fasm` in Arch extra). For reproducible builds, pin the exact release tarball and checksum rather than tracking "latest".

## Pitfalls that cost real debugging time

**YASM's instruction gap is silent until it is not.** If you are parsing generated assembly from a modern compiler, the compiler will emit encodings YASM does not know. Do not put YASM in a pipeline that compiles today's intrinsics.

**NASM will happily assemble a broken stack.** Without `section .note.GNU-stack` you get an executable stack, which fails hardening checks and sometimes segfaults under SELinux policies. Add the section to every file, or pass `-z noexecstack` at link time.

**Absolute addressing breaks under PIE.** NASM defaults to absolute addresses for `[symbol]` operands. Add `default rel` at the top of the file, or your freestanding code will fail to link into a PIE with "relocation R_X86_64_32S against ... can not be used when making a PIE object".

**FASM's `format` line is not optional.** Omitting `format ELF64 executable 3` gives you a flat binary, and the kernel will refuse to exec it with a confusing `ENOEXEC`. The `3` is the ELF OSABI value for Linux.

**Debug info and optimization levels interact.** NASM's `-Ox` enables multipass optimization for jump sizing; combined with `-g -F dwarf` this is fine, but mixing `-O0` with long macros can produce short-jump overflow errors that vanish at `-Ox`.

**Do not benchmark assemblers on hello world.** The interesting difference is macro expansion and symbol resolution on large generated files. NASM and FASM both handle 100k-line generated tables without drama; YASM's older parser is slower on deeply nested macros.

If you also work above the assembly layer, our comparison of [tiny C compilers like TCC, chibicc and cproc](../2026-09-24-tcc-vs-chibicc-vs-cproc-tiny-c-compilers/) covers the next rung up the toolchain, and the [assembler and disassembler engine comparison](../2026-06-21-assembler-disassembler-engines-capstone-keystone-unicorn-udis86/) covers the library side if you need to encode or decode instructions at runtime. For targets that are not x86 at all, see the [WebAssembly toolchain breakdown](../2026-09-11-webassembly-toolchains-emscripten-tinygo-assemblyscript/).

## FAQ

### Is NASM still maintained in 2026?

Yes. The `netwide-assembler/nasm` repository has roughly 3,365 stars and receives commits continuously — the most recent push at the time of writing was 2026-08-19. Releases track current x86 extensions, and it is packaged in every major distribution.

### Can I replace YASM with NASM without changing my source?

For NASM-dialect sources, usually yes. NASM is the dialect YASM copied, so `-f elf64`, `%macro`, `section` and `global` all work. You will need to replace YASM-only features such as `-p gas`, `-r cpp` and `-g dwarf2` (NASM uses `-g -F dwarf`). Test the output with `objdump -d` before trusting the swap.

### Does FASM need a linker?

No, for flat formats. `format binary`, `format ELF64 executable`, and the PE/MZ formats are all written directly by FASM in a single pass. That is why FASM is popular for bootloaders, shellcode and size-constrained payloads. For relocatable objects it can still emit COFF/ELF objects that a linker consumes.

### Which assembler produces the smallest binary?

FASM, in practice, because there is no linker inserting alignment padding or merging sections. The difference is most visible in the 200-byte to 4-kilobyte range. For anything above a few tens of kilobytes, the code itself dominates and the choice of assembler stops mattering for size.

### Is assembly worth learning in 2026?

For most application developers, no — but for four specific jobs it is not optional: boot and firmware bring-up, cryptographic primitives where constant-time behavior must be guaranteed at the instruction level, binary-size-constrained targets, and performance work where you need to read what the compiler actually emitted. In all four, the assembler you pick is NASM or FASM.

### What about GAS and the LLVM integrated assembler?

They are the right answer when you are already inside a GCC or Clang build and just need `.s` files assembled. They are the wrong answer when you want a self-contained tool with a documented macro system and a stable CLI — which is the niche NASM and FASM occupy.

---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "NASM vs YASM vs FASM in 2026: Which x86 Assembler Should You Actually Use?",
  "description": "Hands-on comparison of NASM, YASM and FASM: syntax, output formats, macro systems, maintenance status, build commands and pitfalls.",
  "datePublished": "2026-11-19",
  "dateModified": "2026-11-19",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
