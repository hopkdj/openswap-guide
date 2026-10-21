---
title: "Smart Contract Toolchains in 2026: Foundry vs Hardhat vs Brownie (Truffle Is Dead)"
date: "2026-10-22"
tags: ["blockchain", "ethereum", "solidity", "developer-tools"]
draft: false
---

In September 2023 ConsenSys sunset Truffle. Three years later its repository still carries **13,903 stars** — more than any living competitor — and its last commit is dated **2024-04-22**. That gap between popularity and maintenance is the clearest lesson in smart contract tooling: star counts measure history, not health. Teams that picked Truffle by stars spent 2024 migrating under deadline.

This guide compares the toolchains that genuinely carry production work in 2026 — **Foundry**, **Hardhat**, and **Brownie**, with **Ape** as the Python-side alternative — using live repository data, real configuration, and the failure modes each one produces under pressure.

## TL;DR: Pick By Language, Then By Testing Style

- **Solidity-first team that lives in the terminal** → **Foundry**. Fastest test loop, best fuzzing, `cast` and `anvil` replace half your scripts.
- **TypeScript team, existing Hardhat plugins, deploy scripts already in JS/TS** → **Hardhat**. Mature ecosystem, Ignition deployments, and a debugger worth using.
- **Python team doing data-heavy or research work around contracts** → **Brownie** for smaller projects, **Ape** for active long-term work (Ape's last commit is October 2026; Brownie's is August 2026).
- **Still on Truffle** → migrate now. `hardhat` has an official migration path; Foundry's is a rewrite of scripts but a mechanical one.
- **Do not choose a toolchain by star count.** Truffle has the most stars of anything in this table and is the only one you should not start with.

## Comparison Table (Live Repository Data, October 2026)

| Toolchain | Stars | Last commit | Language | Test runner | Fuzzing / invariants | Fork testing | Deployment story | Debugging |
|---|---|---|---|---|---|---|---|---|
| **Foundry** (`foundry-rs/foundry`) | 10,685 | 2026-10-21 | Rust binary, Solidity tests | `forge test` | **Yes, built in** (`--fuzz-runs`, invariants) | **Yes** (`--fork-url`) | `forge script` | Traces via `-vvvv` |
| **Hardhat** (`NomicFoundation/hardhat`) | 8,517 | 2026-10-21 | TypeScript | Mocha + Chai / Node test runner | Partial (via plugins) | **Yes** (`forking.url`) | **Ignition** modules | Solidity stack traces, `console.log` |
| **Brownie** (`eth-brownie/brownie`) | 2,719 | 2026-08-05 | Python | pytest | Limited | Yes (`mainnet-fork`) | `scripts/deploy.py` | `--interactive`, tracebacks |
| **Ape** (`ApeWorX/ape`) | 1,054 | 2026-10-21 | Python | pytest | Limited | Yes | `ape run deploy` | Rich tracebacks, `ape console` |
| **Truffle** (`trufflesuite/truffle`) | 13,903 | 2024-04-22 (sunset) | JavaScript | Mocha | No | Limited | `truffle migrate` | Weak |

The two live leaders differ by philosophy, not by capability checklist: Foundry compiles Solidity and runs tests written in Solidity; Hardhat compiles Solidity and runs tests written in TypeScript.

## Decision Matrix

| Your situation | Choose | Why |
|---|---|---|
| New protocol with heavy math and invariants | Foundry | Invariant testing catches accounting bugs that unit tests miss |
| Team of TypeScript developers, no Rust tooling | Hardhat | Everyone already knows the test language |
| Deploy scripts that must integrate with a web app | Hardhat | Ignition plus the same package ecosystem as your frontend |
| Research notebook workflow, Python analysis | Ape | Plugin architecture, `ape console`, pytest-native |
| Small Python project, quick prototype | Brownie | Lowest setup cost for a throwaway fork test |
| Existing Truffle project, 12 months of scripts | Hardhat | Official migration path reduces the diff |
| CI where test runtime is the bottleneck | Foundry | No Node process, no compilation of test files in JS |

## Foundry — The Terminal-Native Toolchain

Foundry installs as native binaries. `forge` compiles and tests, `cast` talks to the chain, `anvil` runs a local node, and `chisel` is a Solidity REPL.

```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup

forge init my-protocol && cd my-protocol
forge build
forge test -vvv
forge test --match-test testFuzz_Deposit --fuzz-runs 50000
```

Configuration lives in `foundry.toml`, and pinning the compiler and RPC endpoints there is what keeps builds reproducible:

```toml
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
solc_version = "0.8.28"
optimizer = true
optimizer_runs = 200
fuzz = { runs = 512 }
invariant = { runs = 256, depth = 64 }
gas_reports = ["Vault", "Router"]

[rpc_endpoints]
mainnet = "${MAINNET_RPC_URL}"
arbitrum = "${ARBITRUM_RPC_URL}"
```

Tests are Solidity contracts, which removes the language boundary entirely:

```solidity
// test/Vault.t.sol
pragma solidity ^0.8.28;
import {Test} from "forge-std/Test.sol";
import {Vault} from "../src/Vault.sol";

contract VaultTest is Test {
    Vault vault;
    address alice = address(0xA11CE);

    function setUp() public {
        vault = new Vault();
        vm.deal(alice, 100 ether);
    }

    function testFuzz_DepositNeverMintsMoreShares(uint96 amount) public {
        vm.assume(amount > 0 && amount < 50 ether);
        vm.prank(alice);
        vault.deposit{value: amount}();
        assertLe(vault.totalSupply(), address(vault).balance);
    }
}
```

Fork testing is one flag away, which is how most teams debug against real mainnet state:

```bash
forge test --fork-url $MAINNET_RPC_URL --fork-block-number 21200000 -vvvv
```

**Where it hurts:** Foundry assumes comfort with a terminal and with Solidity as a test language. Frontend developers on the team will not read your tests, and TypeScript tooling (typechain-style bindings) needs generation steps that Hardhat gives you for free.

## Hardhat — The Ecosystem Play

Hardhat 3 keeps the familiar TypeScript workflow and adds a faster compilation pipeline, but the essentials are unchanged: a config file, a plugin ecosystem, and tests in JS/TS.

```bash
npm init -y
npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox
npx hardhat init
```

```ts
// hardhat.config.ts
import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";

const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.28",
    settings: { optimizer: { enabled: true, runs: 200 } },
  },
  networks: {
    hardhat: {
      forking: { url: process.env.MAINNET_RPC_URL!, blockNumber: 21200000 },
    },
    arbitrum: {
      url: process.env.ARBITRUM_RPC_URL!,
      accounts: [process.env.DEPLOYER_KEY!],
    },
  },
};

export default config;
```

Deployments in 2026 go through Ignition, which makes deployment a declarative module instead of an imperative script — the feature that most often decides the choice for teams shipping to multiple chains:

```ts
// ignition/modules/Vault.ts
import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

export default buildModule("VaultModule", (m) => {
  const owner = m.getAccount(0);
  const vault = m.contract("Vault", [owner]);
  m.call(vault, "setFeeRecipient", [owner]);
  return { vault };
});
```

```bash
npx hardhat ignition deploy ignition/modules/Vault.ts --network arbitrum
```

**Where it hurts:** the Node toolchain is heavy, tests are slower than Forge for the same assertions, and fuzzing is plugin-dependent rather than a first-class mode. Also: TypeScript test code drifts from contract types unless you regenerate bindings in CI.

## Brownie and Ape — The Python Side

Brownie is the tool that made Python contract testing approachable, and it still works well for small projects:

```bash
pipx install eth-brownie
brownie init
brownie compile
brownie test --coverage
brownie run scripts/deploy.py --network mainnet-fork
```

```yaml
# brownie-config.yaml
networks:
  default: mainnet-fork
  mainnet-fork:
    fork: mainnet
compiler:
  solc:
    version: "0.8.28"
    optimizer:
      enabled: true
      runs: 200
```

Ape is the actively developed successor in spirit: plugin-based, pytest-native, with a persistent console that is genuinely useful for exploring deployed state.

```bash
pipx install eth-ape
ape plugins install solidity etherscan
ape compile
ape test -v
ape console --network ethereum:mainnet
```

**Where they hurt:** both trail Foundry and Hardhat on fuzzing and on multi-chain deployment ergonomics, and their plugin ecosystems are smaller. Ape's October 2026 commit cadence versus Brownie's August 2026 is the signal you should act on when starting something new.

## Does Toolchain Speed Actually Change How You Work?

Yes — through iteration count, not through benchmark bragging. A test suite you can run in seconds gets run on every save; one that takes ninety seconds gets run before pushing. Invariant testing in particular is only practical when a run finishes fast enough to survive a CI job.

Measure your own project rather than trusting comparisons:

```bash
# Foundry
time forge test

# Hardhat
time npx hardhat test

# Brownie / Ape
time brownie test
time ape test
```

Then compare like for like: the same contract, the same assertions, fork disabled. Foundry usually wins the compile-and-test loop because there is no Node process and no JS test compilation, but the gap narrows on suites dominated by RPC calls to a fork — network latency, not the tool, becomes the bottleneck.

## Pitfalls That Cause Real Losses

**Private keys in shell history.** `--private-key 0x...` on the command line ends up in `~/.bash_history`, CI logs, and screen shares. Use `cast wallet import deployer --interactive` and reference the keystore account, or an environment variable injected by your CI secret store. Rotate immediately if a key ever appeared in a log.

**Unpinned fork blocks.** `--fork-url` without a block number makes tests depend on whatever the chain looked like this morning. Pin the block; when a test starts failing mysteriously, you will know it is your code.

**Compiler version drift.** A `pragma` range of `^0.8.0` plus a floating compiler means two developers can produce different bytecode. Pin `solc_version` (Foundry), `solidity.version` (Hardhat), or `compiler.solc.version` (Brownie), and commit the lockfile.

**Gas snapshot churn.** Foundry's `forge snapshot` is useful until it becomes a merge-conflict generator. Store snapshots per branch or gate them behind a label; reviewing 400 changed gas numbers in one PR teaches nobody anything.

**Invariant tests that never fail.** An invariant suite with no handler contract and a shallow depth proves nothing. Give handlers bounded inputs, set `depth` high enough to reach multi-call sequences, and verify the suite fails when you deliberately break accounting.

**Deterministic addresses across chains.** `CREATE2` deployments need the same salt, init code, and factory address. Foundry's `vm.computeCreate2Address` and Hardhat's `getCreate2Address` are how you assert the address before deploying rather than after.

**RPC rate limits in CI.** Free RPC endpoints throttle; a fork-based suite that passes locally will fail intermittently in CI. Cache fork state locally (`anvil --fork-url ... --dump-state`) or use a paid endpoint for CI only.

## Migration and Coexistence Notes

Truffle → Hardhat is the low-friction path: contracts and migrations map onto Hardhat's structure, and the plugin ecosystem covers most of what Truffle did. Truffle → Foundry is more work up front because deploy scripts become Solidity scripts, but the resulting suite is usually smaller and faster.

Running two toolchains side by side is common and reasonable: Foundry for unit and invariant tests, Hardhat for deployment and frontend bindings. Keep one source of truth for compiler settings — a shared `foundry.toml` and `hardhat.config.ts` that disagree on optimizer runs will produce bytecode that fails verification on block explorers.

Whatever you pick, two habits matter more than the tool: commit the lockfile, and keep a deploy script that can be dry-run against a fork before it touches a real network.

If you are running your own infrastructure around this, our [Ethereum node client comparison](../2026-05-03-geth-vs-erigon-vs-reth-self-hosted-ethereum-node-clients-guide-2026/) covers what to sync behind your fork tests, the [blockchain data indexer guide](../2026-06-15-self-hosted-blockchain-data-indexers-graph-subsquid-subquery/) covers reading contract events at scale, and the [layer 2 scaling comparison](../2026-06-15-self-hosted-ethereum-layer2-scaling-polygon-edge-optimism-arbitrum/) explains where your contracts actually get deployed.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Smart Contract Toolchains in 2026: Foundry vs Hardhat vs Brownie (Truffle Is Dead)",
  "description": "Foundry, Hardhat, Brownie and Ape compared for smart contract development in 2026: live repository data, working configuration, fuzzing and fork testing, plus the pitfalls that cause real losses.",
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

## FAQ

### Is Truffle still usable in 2026?

No. The Truffle Suite was sunset in September 2023 and the repository's last commit is April 2024. It receives no security fixes and its dependency tree is unmaintained. Existing projects should migrate to Hardhat (lowest friction) or Foundry (better test loop).

### Foundry or Hardhat for a new Solidity project?

Choose Foundry if your team is comfortable in a terminal and you want first-class fuzz and invariant testing. Choose Hardhat if your team writes TypeScript daily, needs Ignition-style declarative deployments, or must share types with a frontend. Many teams run both: Foundry for tests, Hardhat for deployment.

### Can I write tests in Solidity and still deploy with TypeScript?

Yes, and it is a common split. Keep unit and invariant tests in `forge`, then have Hardhat or a small script consume the compiled artifacts from `out/` for deployment and binding generation. Pin the compiler in both configs so the artifacts match.

### How do I fork mainnet state without paying for an RPC provider?

Run a local node or use `anvil --fork-url` against a public endpoint and dump state with `--dump-state`, then reload it with `--load-state` for offline runs. Public endpoints rate-limit aggressively, so treat them as a bootstrap step rather than a CI dependency.

### What is invariant testing and do I need it?

Invariant testing runs randomized call sequences against your contracts and asserts that properties like "total shares never exceed total assets" always hold. For protocols holding user funds, it is the highest-value test category available — and it is why Foundry's built-in invariant mode matters more than most feature checkboxes.

### Does Brownie still receive updates?

Brownie's repository shows commits in 2026, but cadence is slower than Ape's. For new Python projects, prefer Ape: it is actively developed, plugin-based, and pytest-native. Brownie remains fine for small scripts and existing projects.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
