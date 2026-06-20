---
title: "Self-Hosted Assembler & Disassembler Engines: Capstone vs Keystone vs Unicorn vs udis86 — Programmable Binary Analysis Libraries"
date: "2026-06-21"
tags: ["binary-analysis", "reverse-engineering", "assembler", "disassembler", "c-libraries", "developer-tools", "security"]
draft: false
---

## Why Programmable Disassembly Engines Matter

Low-level binary analysis — reading machine code and reasoning about its behavior — is a foundational capability for reverse engineering, vulnerability research, emulation, and compiler development. Rather than parsing binary formats manually, developers use disassembler and assembler libraries that translate between human-readable assembly mnemonics and raw machine bytes automatically.

These libraries form the engine beneath [binary analysis platforms](../2026-05-03-ghidra-vs-radare2-vs-rizin-self-hosted-binary-analysis-reverse-engineering-guide-2026/) like Ghidra and radare2, and power [compiler exploration tools](../2026-06-18-self-hosted-compiler-explorer-godbolt-code-analysis/) like Godbolt Compiler Explorer. Without a reliable disassembly engine, every binary analysis tool would need to implement instruction decoding from scratch — a monumental task given the complexity of modern instruction sets (ARMv8 alone has over 1,000 instruction encodings).

This article compares four widely-used open-source disassembler and assembler libraries — Capstone, Keystone, Unicorn, and udis86 — across architecture support, API design, performance, and licensing.

## Library Overview

| Feature | Capstone | Keystone | Unicorn | udis86 |
|---------|----------|----------|---------|--------|
| Function | Disassembler | Assembler | CPU Emulator | Disassembler |
| Stars | 8,849 | 2,602 | 9,101 | 1,077 |
| Last Updated | June 2026 | April 2025 | May 2026 | May 2023 |
| License | BSD-3-Clause | GPL-2.0 | GPL-2.0 | BSD-2-Clause |
| Language | C (bindings: Python, Java, Rust, Go, C#) | C (bindings: Python, Node.js, Ruby, Rust) | C (bindings: Python, Java, Rust, Go) | C |
| Architectures | 12+ (ARM, ARM64, x86, MIPS, PPC, Sparc, SystemZ, XCore, BPF, RISCV, etc.) | 8 (ARM, ARM64, Hexagon, MIPS, PPC, Sparc, SystemZ, x86) | 12+ (ARM, ARM64, M68K, MIPS, Sparc, PPC, RISCV, S390X, x86, etc.) | x86 (16/32/64-bit) |
| Instruction-level detail | Full (operand types, access flags, register reads/writes) | Instruction encoding only | Instruction-level execution with memory/register state | Full (operand sizes, prefixes) |
| Output format | Structured decomposition | Raw machine bytes | Emulation state changes | Structured decomposition |

### Capstone — The Ultimate Disassembler

Capstone is a lightweight, multi-architecture disassembly framework designed as the "LLVM of disassemblers." It provides a clean, consistent API across 12+ CPU architectures and returns structured instruction information — not just the mnemonic string, but operand types, implicit register reads/writes, and instruction group classification.

```c
// Capstone disassembly of x86-64 code
#include <capstone/capstone.h>

unsigned char CODE[] = "\x55\x48\x8b\x05\x00\x00\x00\x00";

csh handle;
cs_insn *insn;
size_t count;

if (cs_open(CS_ARCH_X86, CS_MODE_64, &handle) == CS_ERR_OK) {
    count = cs_disasm(handle, CODE, sizeof(CODE)-1, 0x1000, 0, &insn);
    for (size_t i = 0; i < count; i++) {
        printf("0x%"PRIx64": %s %s\n",
            insn[i].address,
            insn[i].mnemonic,    // "push"
            insn[i].op_str);     // "rbp"
        // Access operand details:
        // insn[i].detail->x86.operands[0].type
    }
    cs_free(insn, count);
    cs_close(&handle);
}
```

Capstone's detail mode reveals operand-level information critical for program analysis tools: which registers are read, which are written, whether operands are memory references, and what instruction group (jump, call, return, arithmetic) the instruction belongs to. This is why virtually every modern reverse engineering tool — radare2, x64dbg, Binary Ninja — uses Capstone under the hood.

### Keystone — Programmatic Assembly

Keystone is Capstone's sister project, doing the reverse operation: converting assembly text into machine code bytes. It uses the LLVM assembler infrastructure internally but exposes a simple, language-agnostic C API.

```c
// Keystone assembly — x86-64 code generation
#include <keystone/keystone.h>

ks_engine *ks;
ks_err err;
size_t count;
unsigned char *encode;

err = ks_open(KS_ARCH_X86, KS_MODE_64, &ks);
if (err == KS_ERR_OK) {
    const char *asm_str = "mov rax, 0x1234; push rax; ret";
    if (ks_asm(ks, asm_str, 0, &encode, &size, &count) == 0) {
        printf("Encoded %zu bytes:\n", size);
        for (size_t i = 0; i < size; i++)
            printf("%02x ", encode[i]);
        // Output: 48 c7 c0 34 12 00 00 50 c3
        ks_free(encode);
    }
    ks_close(ks);
}
```

Keystone is essential for tools that generate machine code at runtime — JIT compilers, binary patching frameworks, shellcode generators, and exploit development toolkits. Its Python bindings make it particularly popular in the security research community.

### Unicorn — CPU Emulation as a Library

Unicorn is a lightweight CPU emulator built on QEMU's binary translation engine. Unlike Capstone (which only decodes instructions) and Keystone (which only assembles them), Unicorn actually **executes** instructions in a sandboxed virtual machine environment, tracking register values and memory state.

```python
# Unicorn emulation — execute ARM code
from unicorn import *
from unicorn.arm_const import *

# ARM64 code: mov x0, #42; ret
ARM_CODE = b'\x40\x05\x80\xd2\xc0\x03\x5f\xd6'

mu = Uc(UC_ARCH_ARM64, UC_MODE_ARM)

# Map 2MB of memory at address 0x10000
mu.mem_map(0x10000, 2 * 1024 * 1024)
mu.mem_write(0x10000, ARM_CODE)

# Set up stack
mu.reg_write(UC_ARM64_REG_SP, 0x10000 + 0x100000)

# Emulate until we hit the end of our code block
mu.emu_start(0x10000, 0x10000 + len(ARM_CODE))

# Read return value
x0 = mu.reg_read(UC_ARM64_REG_X0)
print(f"Return value: {x0}")  # 42
```

Unicorn enables powerful use cases: fuzzing individual functions without running the full binary, executing malware in a sandboxed environment, unit-testing assembly-level optimizations, and emulating embedded firmware on a developer's workstation. Combined with Capstone and Keystone, the three libraries form a complete binary analysis toolkit.

### udis86 — Minimalist x86 Disassembler

udis86 is a focused x86/x86-64 disassembler that prioritizes small code size and zero dependencies. At its core is a hand-crafted instruction decoding table derived from Intel's reference manuals.

```c
// udis86 disassembly
#include <udis86.h>

unsigned char code[] = "\x55\x89\xe5\x83\xec\x10\xc9\xc3";

ud_t ud_obj;
ud_init(&ud_obj);
ud_set_mode(&ud_obj, 32);
ud_set_syntax(&ud_obj, UD_SYN_INTEL);
ud_set_input_buffer(&ud_obj, code, sizeof(code) - 1);

while (ud_disassemble(&ud_obj)) {
    printf("0x%016lx: %-20s %s\n",
        ud_insn_off(&ud_obj),
        ud_insn_asm(&ud_obj),
        ud_insn_hex(&ud_obj));
}
```

udis86's value comes from its simplicity: the entire library compiles to about 20 KB of code with no external dependencies. For tools that only need x86 disassembly — such as Linux kernel tracing, JTAG debuggers, or embedded diagnostics — udis86 avoids pulling in the multi-megabyte Capstone library.

## Integration Example: Disassemble-Analyze-Emulate Pipeline

The true power of these libraries emerges when they are combined. Here is a Python pipeline that disassembles a function with Capstone, patches it with Keystone, and verifies the patch with Unicorn:

```python
from capstone import *
from keystone import *
from unicorn import *
from unicorn.x86_const import *

# Step 1: Disassemble with Capstone
original_code = b'\x55\x48\x89\xe5\xb8\x2a\x00\x00\x00\x5d\xc3'
md = Cs(CS_ARCH_X86, CS_MODE_64)
print("Original disassembly:")
for insn in md.disasm(original_code, 0x1000):
    print(f"  0x{insn.address:x}: {insn.mnemonic} {insn.op_str}")

# Step 2: Assemble patched version with Keystone
ks = Ks(KS_ARCH_X86, KS_MODE_64)
asm = "push rbp; mov rbp, rsp; mov eax, 99; pop rbp; ret"
encoding, count = ks.asm(asm)
print(f"\nPatched: {bytes(encoding).hex()}")

# Step 3: Verify with Unicorn
mu = Uc(UC_ARCH_X86, UC_MODE_64)
mu.mem_map(0x1000, 0x1000)
mu.mem_write(0x1000, bytes(encoding))
mu.emu_start(0x1000, 0x1000 + len(encoding))
result = mu.reg_read(UC_X86_REG_RAX)
print(f"\nVerification: RAX = {result} (expected 99)")
```

## Installation

### Building Capstone

```bash
git clone https://github.com/capstone-engine/capstone.git
cd capstone
./make.sh
sudo ./make.sh install

# Python bindings
cd bindings/python
pip install .
```

### Building Keystone

```bash
git clone https://github.com/keystone-engine/keystone.git
cd keystone
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
sudo make install
```

### Building Unicorn

```bash
git clone https://github.com/unicorn-engine/unicorn.git
cd unicorn
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
sudo make install

# Python bindings
pip install unicorn
```

### Building udis86

```bash
git clone https://github.com/vmt/udis86.git
cd udis86
./autogen.sh
./configure
make
sudo make install
```

## Choosing the Right Binary Analysis Library

### When to Choose Capstone

Capstone is the default choice for any project that needs instruction disassembly. Its multi-architecture support, detailed operand analysis, and permissive BSD license make it suitable for everything from open-source reverse engineering tools to commercial security products.

### When to Choose Keystone

Keystone is the right choice when you need to programmatically generate machine code — JIT compilers, binary patchers, exploit payload generators, and assembly-level code transformation tools. Its multi-architecture support means one API works for x86, ARM, MIPS, and other targets.

### When to Choose Unicorn

Unicorn is essential when you need to execute or emulate code in a sandbox — fuzzing harnesses, malware sandboxes, embedded firmware testing, and security CTF challenge solvers. It is the only library in this comparison that supports actual instruction execution with register and memory tracking.

### When to Choose udis86

udis86 is the right choice for x86-only projects with tight size constraints — kernel modules, bootloaders, JTAG debuggers, and embedded diagnostics where pulling in Capstone's full library would be excessive. Its 20 KB binary footprint is unmatched.

## FAQ

### Can I use Capstone and Keystone together in the same project?

Yes, they are designed to be complementary. Capstone disassembles binary → human-readable, Keystone assembles human-readable → binary. Many reverse engineering tools use both: Keystone to generate patch bytes, Capstone to verify the patch disassembles correctly. The APIs are intentionally similar since they come from the same development team.

### What is the difference between Capstone and Unicorn for binary analysis?

Capstone is a **static** analysis tool — it reads bytes and tells you what instructions they represent, but it does not execute them. Unicorn is a **dynamic** analysis tool — it actually runs the instructions in a virtual CPU, tracking register and memory state. Use Capstone to understand what code does at rest, and Unicorn to observe what it does at runtime. For comprehensive analysis, most tools use both.

### Why does Keystone use GPL while Capstone uses BSD?

Capstone and Keystone were developed by the same team (Nguyen Anh Quynh) but with different foundational code. Capstone was written from scratch as a clean-room implementation of instruction decoding. Keystone reuses LLVM's assembler infrastructure (MC layer), which is under LLVM's license — and Keystone's own code layers GPL on top. Unicorn reuses QEMU's binary translation engine, inheriting QEMU's GPL license.

### Can Unicorn emulate real-world binaries like an .exe file?

Unicorn is a CPU emulator, not a full system emulator. It provides raw CPU, memory, and register access but does not emulate an operating system — no process loader, no system call handler, no filesystem, no dynamic linker. To emulate a real binary, you need to load the binary into memory, map its sections, handle system calls yourself (by registering hooks), and emulate any required libraries. Tools like Qiling Framework build on Unicorn to provide full binary emulation.

### Is udis86 still maintained?

udis86's last update was in May 2023 for maintenance fixes. The core x86/x86-64 instruction set is stable (no new encodings have been added to legacy x86 in years). For AVX-512, AMX, and other Intel extensions beyond x86-64 baseline, Capstone provides more comprehensive support. udis86 is best used for legacy x86 analysis or in environments where code size is paramount.

### How do I handle obfuscated or self-modifying code?

Capstone and Keystone operate on static byte sequences — they do not track runtime modifications. For self-modifying code, use Unicorn: write the initial code to emulated memory, emulate it, then read back the modified memory and disassemble with Capstone. Unicorn's hook mechanism allows intercepting memory writes to detect self-modification events in real time.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Assembler & Disassembler Engines: Capstone vs Keystone vs Unicorn vs udis86",
  "description": "Compare open-source binary analysis libraries Capstone, Keystone, Unicorn, and udis86 for disassembly, assembly, and CPU emulation. Covers architecture support, API design, code examples, and a complete disassemble-analyze-emulate pipeline.",
  "datePublished": "2026-06-21",
  "dateModified": "2026-06-21",
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
