# Radiant Protocol v0.1.0 – First Public Release

## 🎉 What’s New
- **Smart Contract**: `Radiant.sol` with staking, proof submission, reputation, rewards, slashing, and council-based emergency governance.
- **Token Contract**: `RadiantShares.sol` (ERC20) with vesting and reputation-weighted rewards.
- **Backend API**: FastAPI server providing CIS scoring (`/score`) and trend analytics.
- **Relayer**: Node.js service that listens to contract events and pushes proofs to Kafka.
- **Rust Worker**: Placeholder for ZK‑recursive proof validation (Nova integration coming soon).
- **WebSocket Server**: Broadcasts validation results to frontend.
- **React Dashboard**: User interface for staking, proof submission, leaderboard, and live updates.
- **Docker Compose**: One‑command local deployment of the entire stack.

## 🚀 Getting Started
See [README.md](README.md) for instructions to run locally or deploy to testnet.

## 📦 Assets
- Smart contracts (Sepolia‑compatible)
- Docker images (published to Docker Hub soon)
- Frontend build (available in `/frontend/build`)

## 🙌 Contributors
- [@1me0](https://github.com/1me0) – architect and initial implementation
