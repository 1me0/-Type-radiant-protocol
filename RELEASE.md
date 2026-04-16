# Radiant Protocol v0.1.0 – First Public Release

*Release Date: April 2026*

Welcome to the first public release of the **Radiant Protocol** – a ZK‑recursive proof‑of‑presence field for verifiable communication, identity, and value.

---

## 🎉 What’s New

This release includes all core components necessary to run a complete instance of the Radiant Protocol on a testnet (Sepolia) or locally.

### Smart Contracts (Solidity)
- `Radiant.sol` – staking, proof submission, reputation, rewards, slashing, council‑based emergency governance.
- `RadiantShares.sol` – ERC20 token with vesting and reputation‑weighted rewards.
- `ArchitectFee.sol` – competitive fee game (50% fee, record‑breaking bonus).
- `Registry.sol` – canonical address registry.
- `LicenseRegistry.sol` – on‑chain license enforcement.

### Backend & Services
- **FastAPI** (`app.py`) – CIS scoring endpoint (`/score`) and trend analytics.
- **Relayer** (Node.js) – listens to contract events, forwards proofs to Kafka.
- **Rust Worker** – placeholder for ZK‑recursive proof validation (Nova integration coming soon).
- **WebSocket Server** – broadcasts validation results to frontend.
- **Kafka** – message bus for proof pipeline.

### Frontend
- **React Dashboard** – staking, proof submission, leaderboard, live proof feed.
- **RadiantPresence.html** – Proof of Presence demo with local storage and on‑chain anchoring.
- **RadiantTransaction.html** – Competitive fee game interface.
- **RadiantSocial.html** – CIS‑gated social feed.

### Infrastructure
- **Docker Compose** – one‑command local deployment of the entire stack.
- **Hardhat** – deployment scripts for Sepolia and other networks.
- **Environment templates** – `.env.example` with clear instructions.

---

## 🚀 Getting Started

See the [README.md](README.md) for:

- Prerequisites (Node.js, Docker, MetaMask)
- Installation steps
- Running the full stack with `docker-compose up`
- Deploying to Sepolia testnet

For a detailed step‑by‑step tutorial, refer to [TUTORIAL.md](TUTORIAL.md).

---

## 📦 Assets

- **Smart contracts** – deployed on Sepolia testnet (addresses available in the registry)
- **Docker images** – coming soon to Docker Hub
- **Frontend build** – `/frontend/build` (static files ready for hosting)
- **SDK** – `RadiantSDK.ts` for TypeScript/JavaScript integrations

---

## 🔒 Security

- **Audit status**: This release has not yet undergone a professional third‑party audit. The contracts have been tested on Sepolia and are considered experimental. A full security audit is planned before mainnet deployment.
- **Bug bounty**: We welcome responsible disclosure of vulnerabilities. Please report security issues via the process in [SECURITY.md](SECURITY.md) – do not use public issues.
- **Key management**: All administrative roles (architect, council, fee recipient) are controlled by the deployer wallet. For mainnet, a multi‑signature wallet (e.g., Gnosis Safe) will be used to reduce centralisation risk.
- **License enforcement**: The `LicenseRegistry` contract enforces commercial licenses on‑chain. Attempts to bypass it void the license.

---

## ⚠️ Known Issues / Limitations

- The Rust worker currently simulates proof validation (actual Nova folding not yet integrated).
- On‑chain anchoring for Proof of Presence requires a deployed `PresenceRegistry` contract (provided).
- WebSocket server is not yet scaled for high concurrency (single instance only).
- The CIS scoring API uses a rule‑based fallback; AI‑powered scoring requires additional setup (see `ai/` directory).

---

## 🗺️ Roadmap (Next Release)

- **Nova integration** – replace the placeholder Rust worker with real recursive proof folding.
- **Mainnet deployment** – deploy contracts to Arbitrum One or Base after audit.
- **Scalability** – horizontal scaling for WebSocket server and Kafka workers.
- **AI improvement** – integrate the fine‑tuned SLM for CIS scoring.
- **Governance** – transition to a multi‑sig or DAO for protocol parameters.

---

## 🙌 Contributors

- **[@1me0](https://github.com/1me0)** – architect and initial implementation

---

## 🔗 Resources

- [GitHub Repository](https://github.com/1me0/Type-radiant-protocol)
- [Documentation](README.md)
- [Security Policy](SECURITY.md)
- [Threat Model](THREAT_MODEL.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)

---

## 📜 License

Core protocol code is licensed under **MIT**.  
Commercial use of fee‑bearing contracts (`RadiantShares`, `ArchitectFee`, etc.) requires a separate commercial license – see [LICENSE_RADIANT.md](LICENSE_RADIANT.md).

---

**Thank you for exploring the Radiant Protocol.**  
*Radiance.*
