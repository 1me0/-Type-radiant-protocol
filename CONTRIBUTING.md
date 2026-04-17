# Contributing to Radiant Protocol

Thank you for your interest in contributing! Radiant is a community‑driven project aiming to build a constitutional layer for communication – a zero‑knowledge proof‑of‑presence field where truth emerges from verifiable interaction.

We welcome contributions of all kinds: code, documentation, design, testing, and community support.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)
- [License](#license)

---

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behaviour by opening an issue (confidential) or emailing the maintainers (address in CODE_OF_CONDUCT.md).

---

## How to Contribute

- **Report bugs** – Open a GitHub Issue with clear steps to reproduce and expected/actual behaviour.
- **Suggest features** – Use GitHub Discussions or an Issue labelled `enhancement`.
- **Submit code** – Fork the repository, create a branch, and open a Pull Request.
- **Improve documentation** – Typos, clarifications, or new tutorials are always welcome.
- **Help others** – Answer questions on Discord or GitHub Discussions.

---

## Development Setup

Follow the [TUTORIAL.md](TUTORIAL.md) to set up your local environment using Docker and Hardhat.

Quick start:

```bash
git clone https://github.com/1me0/Type-radiant-protocol.git
cd Type-radiant-protocol
npm install
npx hardhat compile
docker-compose up --build
