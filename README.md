# Radiant Protocol – Communication Intelligence System

A decentralized protocol that measures, verifies, and rewards communication clarity using ZK‑recursive proofs.

## Features

- Staking, reputation, and reward system on Ethereum.
- Real‑time scoring via CIS formula (Alignment, Understanding, Accuracy, Distortion).
- Kafka‑based proof pipeline with Rust workers.
- WebSocket dashboard for live updates.
- React frontend with wallet integration.

## Getting Started

1. Clone the repository.
2. Deploy the contract to Ganache (or a testnet) and update `docker-compose.yml` with the contract address.
3. Run `docker-compose up --build`.
4. Open `http://localhost:3000` to view the dashboard.
5. Use `http://localhost:8000/docs` for the scoring API.

## Architecture

- **Smart Contract** – Handles staking, proofs, and rewards.
- **Relayer** – Listens for contract events and pushes to Kafka.
- **Worker** – Validates proofs (simulated) and publishes results.
- **WebSocket Server** – Broadcasts validation results to frontend.
- **Frontend** – React app with wallet connection and live updates.
- **Backend API** – FastAPI server for CIS scoring and trends.

## License

MIT
