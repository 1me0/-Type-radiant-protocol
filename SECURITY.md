# Security Policy: Radiant Protocol

## Supported Versions
| Version | Supported          |
| ------- | ------------------ |
| v0.1.0  | :white_check_mark: |

## Reporting a Vulnerability

The Radiant Protocol operates on the principle of **Sovereign Clarity** – we believe in transparent, responsible disclosure that respects user autonomy and data ownership.

If you discover a security vulnerability, **please do not report it via public issues**. Instead:

1. **Do not disclose the vulnerability publicly** until it has been addressed.
2. Send a detailed report via private email to: **security@radiant‑protocol.org** (PGP key available at [link]).
3. Include clear steps to reproduce, potential impact, and any suggested fixes.
4. We will acknowledge your report within **72 hours** and work with you to resolve the issue. A timeline for a fix will be communicated after initial triage.

If the issue involves a compromise of your own keys, rotate them immediately before contacting us.

## Scope

We are primarily concerned with vulnerabilities in:
- Smart contracts (`Radiant.sol`, `RadiantShares.sol`)
- The relayer and worker services (Rust/Node.js)
- The WebSocket server and frontend authentication flows
- Any component that handles private keys or user data

Out of scope are third‑party dependencies, social engineering, or physical attacks.

## Key Rotation Log

- **2026-03-31:** An early development key used during internal testing was rotated. No production systems were affected.

## Acknowledgments

We appreciate responsible disclosures and will publicly credit reporters (unless they wish to remain anonymous) after fixes are deployed.
