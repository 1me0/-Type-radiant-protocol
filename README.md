
```markdown
# Radiant Protocol

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![ZK](https://img.shields.io/badge/ZK-Recursive-blue)](https://github.com/1me0/Type-radiant-protocol)
[![Solidity](https://img.shields.io/badge/Solidity-0.8.19-black)](https://soliditylang.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2-blue)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.9+-blue)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-compose-2496ED?logo=docker)](https://www.docker.com/)

**Proof of Presence via Recursive Zero‑Knowledge Arguments**

Radiant Protocol turns *presence*—the fact that you were actively responsive within a specific time window—into a verifiable, composable, and valuable resource, without revealing sensitive information. It’s the foundation for a new internet where your attention and real‑time participation are **provable assets**.

---

## 📖 Table of Contents

- [🌟 What is Radiant?](#-what-is-radiant)
- [⚙️ How It Works (in 30 Seconds)](#-how-it-works-in-30-seconds)
- [🧠 Technical Digest](#-technical-digest)
  - [Presence Event](#presence-event)
  - [Recursive Proof Composition](#recursive-proof-composition)
  - [Security & Adversarial Analysis](#security--adversarial-analysis)
- [🚀 Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Quick Demo (Browser)](#quick-demo-browser)
  - [Run the Full Stack Locally](#run-the-full-stack-locally)
- [📜 Smart Contracts](#-smart-contracts)
- [🌐 Demo Apps](#-demo-apps)
- [🛠️ SDK](#-sdk)
- [📚 In-Depth Documentation](#-in-depth-documentation)
- [🗺️ Roadmap](#-roadmap)
- [🤝 Contributing](#-contributing)
- [🔒 Security & Audit](#-security--audit)
- [📄 License](#-license)

---

## 🌟 What is Radiant?

Today’s systems know **who you are** (identity) and **what you own** (assets).  
But they don’t know **whether you are actually here, right now**.

Radiant fills that gap. It uses **zero‑knowledge proofs** and **blockchain randomness** to prove that an entity was **actively responsive within a constrained time window**—without revealing any private data.

**Think of it as:**
- **Proof of attendance** for DAOs, voting, airdrops.
- **Anti‑bot / anti‑Sybil** for social platforms and games.
- **Verifiable human presence** for AI systems.
- **Reputation** that decays when you’re not there.

---

## ⚙️ How It Works (in 30 Seconds)

1. **A challenge is broadcast** – a random value derived from the latest block hash.
2. **You sign the challenge** and your action, then wrap everything in a ZK proof that also proves you hold the minimum stake (1000 RAD).
3. **Multiple presence events are folded recursively** into a single, constant‑size proof using a Nova‑style folding scheme.
4. **A smart contract verifies** only the final aggregated proof in constant time.

The result: you can prove you were present over days, weeks, or years — with **O(1) on‑chain cost**, no matter how many events.

---

## 🧠 Technical Digest

### Presence Event

A *presence event* is the atomic unit:

```

e = (u, a, t, σ, c, σ_c, π_s)

```

- `u` – your public key
- `a` – what you did
- `t` – block height
- `σ` – signature over (u, a, t)
- `c` – fresh challenge (hash of previous block)
- `σ_c` – signature over the challenge
- `π_s` – ZK proof that your stake ≥ 1000 RAD

All sensitive items (`c`, `σ_c`, `π_s`) stay **private** inside the ZK circuit; the verifier only sees the final proof and a Merkle root.

### Recursive Proof Composition

We use a folding scheme to aggregate proofs:

```

Π_{n+1} = Fold(Π_n, π_{n+1})

```

- **Constant size** – the aggregated proof `Π_n` stays ~10 kB regardless of `n`.
- **Constant verification time** – the on‑chain contract verifies `Π_n` in a single step.

### Security & Adversarial Analysis

| Attack | Mitigation |
|--------|------------|
| Replay | Fresh challenge from each block |
| Sybil | Economic: minimum stake of 1000 RAD |
| Long‑range | Block‑anchored timestamps |
| Miner bias | Cost of withholding blocks bounds miner influence |

**Soundness** is proven via a game‑based reduction: forgery is as hard as breaking the underlying signature or hash, or spending more than the total staked value.

For the full threat model and proofs, see [`SECURITY.md`](SECURITY.md) and the [whitepaper](paper.tex).

---

## 🚀 Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) ≥ 18
- [MetaMask](https://metamask.io/) browser extension
- [Docker](https://www.docker.com/) (optional, for full‑stack)
- Sepolia testnet ETH (free faucet: [sepoliafaucet.com](https://sepoliafaucet.com/))

### Quick Demo (Browser)

You can try several demo apps **right now**, no installation needed:

| Demo | File | Description |
|------|------|-------------|
| **Proof of Presence** | `RadiantPresence.html` | Register a presence score from your wallet or name |
| **Transaction Fee Game** | `RadiantDemo.html` | Send RAD, break the record, earn a bonus |
| **CIS‑Gated Social Feed** | `RadiantSocial.html` | Post content rated by high‑CIS users; backed by IPFS |

Just open any of these HTML files in your browser (they run locally).  
For the social feed, you’ll need a Pinata JWT (or enable P2P mode) to upload images.

### Run the Full Stack Locally

```bash
git clone https://github.com/1me0/Type-radiant-protocol.git
cd Type-radiant-protocol

# Install dependencies
npm install

# Start all services (Kafka, Relayer, WebSocket, API, Frontend)
docker-compose up -d
```

Now open http://localhost:3000 – you’ll see the React Dashboard with staking, proof submission, and a live feed.

To deploy your own smart contracts (Sepolia testnet):

```bash
cp .env.example .env
# edit .env with your private key and RPC URL
npx hardhat run scripts/deploy.js --network sepolia
```

After deployment, update the contract addresses in the frontend .env.

---

📜 Smart Contracts

Contract Responsibility
Radiant.sol Core protocol: staking, proofs, rewards, slashing, council governance
RadiantShares.sol ERC‑20 token with max supply 100M, 1% transfer tax, mint timelock
ArchitectFee.sol Competitive fee game: 50% fee to architect, record‑breaking bonus
Registry.sol Canonical address registry (all contracts discoverable here)
RadiantIdentity.sol Library implementing the formal theorem of non‑duality (𝕀)
LicenseRegistry.sol On‑chain license enforcement for commercial use

All contracts are Solidity ^0.8.19 and use OpenZeppelin libraries.

---

🌐 Demo Apps

HTML File Description
RadiantPresence.html Deterministic presence score, local storage, and on‑chain anchoring
RadiantDemo.html Full protocol simulation: presence, CIS scoring, transfer fee game, staking
RadiantSocial.html Decentralised social feed with IPFS, wallet‑based identity, weighted ratings, and togglable P2P (GossipSub)

These demos are self‑contained and run entirely in your browser. They communicate with smart contracts only if you choose to set a contract address.

---

🛠️ SDK

A TypeScript SDK is available for developers who want to integrate Radiant into their dApps or bots.

```ts
import { RadiantSDK } from './RadiantSDK';

const sdk = new RadiantSDK('0xYourContractAddress', signer);
await sdk.stake('0.01');                // stake ETH
await sdk.submitProof('0xhash...');     // submit a proof hash
await sdk.claim();                      // claim rewards
const stats = await sdk.loadUserStats(address); // get stake, reputation, rewards
```

See RadiantSDK.ts for full documentation.

---

📚 In-Depth Documentation

· 📘 Whitepaper (LaTeX) – formal protocol definition, security proofs, adversarial analysis.
· 📝 Release Notes – what’s new in v0.1.0.
· 🔧 Tutorial – detailed setup guide for local and testnet deployment.
· 🛡️ Security & Threat Model – known risks, mitigations, and responsible disclosure.
· 🧬 Threat Model – systematic analysis of attack vectors.
· 🤝 Contributing Guidelines – how to get involved.
· 💎 Code of Conduct – community standards.

---

🗺️ Roadmap

v0.2.0 (Coming Soon)

· Nova integration – real recursive proof folding (replacing placeholder worker)
· Mainnet deployment – Arbitrum One / Base after audit
· Scalability – horizontal scaling for WebSocket & Kafka

v1.0.0

· Mobile wallet – proof‑of‑presence on the go
· Governance – multi‑sig / DAO for protocol parameters
· AI‑powered CIS – fine‑tuned language model for communication scoring

---

🤝 Contributing

We welcome contributions! Please read CONTRIBUTING.md for guidelines on:

· Reporting bugs
· Suggesting features
· Submitting pull requests
· Coding standards

---

🔒 Security & Audit

· Current status: Experimental (Sepolia testnet). A full third‑party audit is planned before mainnet.
· Bug bounty: Report vulnerabilities via SECURITY.md process. Do not use public issues.
· Key management: All admin roles are currently held by the deployer. For mainnet, a Gnosis Safe multi‑sig will be used.

---

📄 License

The core protocol (Solidity, Python, TypeScript) is licensed under MIT.

Commercial use of the Master Formula / LaTeX documentation may require a separate license – see LICENSE_RADIANT.md.

---

Thank you for exploring the Radiant Protocol.
Radiance.

```
