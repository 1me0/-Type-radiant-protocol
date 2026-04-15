# Security Policy: Radiant Protocol

## Supported Versions

| Version | Supported |
| ------- | ------------------ |
| v0.1.0  | ✅ |

## Reporting a Vulnerability

The Radiant Protocol operates on the principle of **Sovereign Clarity** – we believe in transparent, responsible disclosure that respects user autonomy and data ownership.

If you discover a security vulnerability, **please do not report it via public issues**. Instead:

1. **Do not disclose the vulnerability publicly** until it has been addressed.
2. Send a detailed report via encrypted email to: `security@radiant‑protocol.org`
   - **PGP Fingerprint:** `ABCD 1234 5678 90EF ABCD 1234 5678 90EF 1234 5678`  
     (Public key available at [https://radiant‑protocol.org/security.asc](https://radiant‑protocol.org/security.asc))
3. Include clear steps to reproduce, potential impact, and any suggested fixes.
4. We will acknowledge your report within **72 hours** and work with you to resolve the issue.
5. A timeline for a fix will be communicated after initial triage. We aim to release a patch within **90 days** of notification, depending on severity.
6. If the issue involves a compromise of your own keys, rotate them immediately before contacting us.

## Responsible Disclosure Guidelines

- Please avoid testing vulnerabilities on the mainnet production environment. Use testnet or a local fork.
- Do not exploit any vulnerability for personal gain or to harm users.
- Allow reasonable time for the fix before any public disclosure.

## Scope

We are primarily concerned with vulnerabilities in:

- Smart contracts (`Radiant.sol`, `RadiantShares.sol`, `ArchitectFee.sol`, etc.)
- The relayer and worker services (Rust/Node.js)
- The WebSocket server and frontend authentication flows
- Any component that handles private keys or user data

**Out of scope** are third‑party dependencies, social engineering, or physical attacks.

## Bug Bounty

At this time, we do not offer a monetary bug bounty program. However, we will publicly acknowledge all valid reporters (unless they wish to remain anonymous) and may offer non‑financial recognition (e.g., inclusion in a hall of fame).

## Key Rotation Log

- **2026-03-31:** An early development key used during internal testing was rotated. No production systems were affected.

## Acknowledgments

We appreciate responsible disclosures and will publicly credit reporters (unless they wish to remain anonymous) after fixes are deployed. Thank you for helping keep the Radiant Protocol secure.

---

*This policy is subject to change. The latest version is always available in this repository.*
