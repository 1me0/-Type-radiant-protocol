Radiant Protocol

A ZK‑Recursive Proof‑of‑Presence Field
Verify presence. Prove action. Transact trustlessly.

Radiant Protocol introduces a new primitive for the internet: proof of presence – a cryptographic guarantee that an entity truly existed, was active, and acted in a specific moment, without revealing unnecessary data.

Built on recursive zero‑knowledge proofs (ZK‑recursive), Radiant turns presence into a verifiable, composable, and valuable resource.

---

🚀 30‑Second Overview

Radiant answers one question with mathematical certainty:

“Was this entity truly present, active, and valid at this moment?”

It does this by:

· Generating lightweight cryptographic proofs of presence
· Recursively linking proofs across time and systems
· Enabling trustless interaction, identity, and value exchange

The result: a continuous, verifiable chain of being there.

---

🧠 Core Idea

Most systems verify who you are (identity).
Radiant verifies that you were there (presence).

This shifts the foundation from:

```
Identity → Claims → Trust
```

to:

```
Presence → Proof → Verification
```

It creates a new layer where actions, participation, and existence become verifiable and interoperable.

---

⚙️ What It Enables

Capability Description
Trustless Identity Beyond static wallets – presence as a dynamic credential
Proof‑of‑Action Verify real activity, not just assertions
Presence‑Based Transactions Value tied to actual participation, not just ownership
Decentralized Coordination Systems that respond to real‑time existence
Cross‑System Composability Presence proofs from one domain can be used in another

---

🧩 Architecture

Radiant is a full‑stack protocol composed of:

· Smart Contracts (contracts/) – Registry, token, fee logic, staking, and verification
· SDK & Core Logic (RadiantSDK.ts, RadiantDiscovery.ts) – Developer integration interfaces
· Frontend Layer (RadiantPresenceUI.tsx, frontend/) – User interaction and presence visualization
· Backend Services (backend/, Relayer/, Worker/, Websocket/) – Event processing, relaying, real‑time communication
· Deployment & Infra (ignition/, docker-compose.yml) – Multi‑chain and containerized deployment

All components are open source (MIT) and designed for modular use.

---

🔐 How It Works (Simplified)

1. A user or system generates a presence event (e.g., a message, a stake, a login).
2. The event is encoded into a zero‑knowledge proof (ZK proof) – revealing no extra data.
3. Proofs are recursively linked over time using Nova folding, creating a single compact proof.
4. The network verifies the proof, confirming presence without exposing sensitive information.

Result: A continuous, verifiable chain of “being there” – lightweight enough for high‑frequency interactions.

---

📦 Example Use Cases

· Decentralized social networks – prove you participated in a conversation without leaking content.
· Secure communication layers – verify message delivery and read receipts.
· On‑chain reputation – earn reputation for consistent presence, not just token holdings.
· Autonomous coordination – DAOs that require proof of attendance for voting.
· Gaming & virtual worlds – prove you were at an event to claim rewards.

---

🛠️ Getting Started

```bash
# Clone the repository
git clone https://github.com/1me0/Type-radiant-protocol.git
cd Type-radiant-protocol

# Install dependencies
npm install

# Run the full stack locally (Docker required)
docker-compose up

# Start development (frontend only)
npm run dev
```

For a detailed step‑by‑step guide, see TUTORIAL.md.

---

📜 Philosophy

Radiant is built on a single principle:

Truth is not identity. Truth is presence.

Identity can be faked, borrowed, or stolen. Presence – being there, acting, existing in a moment – is the only thing that cannot be delegated without cost. By making presence verifiable, Radiant restores trust to systems that have lost it.

---

🤝 Contributing

We welcome contributors who want to build the future of presence‑based systems.

· Read CONTRIBUTING.md
· Review THREAT_MODEL.md
· Follow CODE_OF_CONDUCT.md

---

⚠️ Status

🚧 Early‑stage protocol under active development.
Expect rapid iteration. Testnet deployments are live; mainnet launch planned after audit.

---

📌 Final Note

Radiant is not just a tool – it is a shift in perspective:

Old Paradigm New Paradigm
Identity Presence
Claims Proof
Static trust Verifiable history
Who you are That you were there

A system where being there is the foundation of truth.

---

📄 License

MIT – open for innovation and expansion.
License fee required for commercial use – see LICENSE.md and LicenseRegistry contract.
