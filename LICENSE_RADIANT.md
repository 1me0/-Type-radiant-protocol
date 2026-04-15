# Radiant Protocol Commercial License (RPL) v1.0

**Copyright © 2026 [Your Name / 1me0]. All rights reserved.**

This license applies specifically to the `RadiantShares` token contract, the `ArchitectFee` contract, and any other smart contracts or software components that implement fee-bearing mechanisms or tokenomics. The core protocol (ZK circuits, SDK, frontend, documentation) is licensed under the MIT License (see `LICENSE` file).

---

## 1. Grant of License

Subject to payment of the required license fee (as defined in the `LicenseRegistry` contract) and compliance with all terms below, you are granted a non‑exclusive, non‑transferable, worldwide license to:

- Use, copy, modify, and distribute the Licensed Software for commercial purposes;
- Deploy the Licensed Software on any public blockchain;
- Integrate the Licensed Software into products or services that generate revenue.

The license fee is a **one‑time payment** per deploying entity (individual or organization). Payment is made by calling `purchaseLicense()` on the official `LicenseRegistry` contract. The fee amount is set by the architect and may change; however, fees paid are final and non‑refundable.

---

## 2. Ownership and Attribution

All copies of the Licensed Software (modified or unmodified) must retain:

- This license file (`LICENSE_RADIANT.md`);
- A visible attribution to the original author (e.g., in source code headers, in the user interface, or in the documentation).

You may not remove or obscure any copyright notices.

---

## 3. Commercial Use Definition

“Commercial use” includes, but is not limited to:

- Running the Licensed Software as a service for which you charge fees;
- Integrating the Licensed Software into a product that generates revenue (directly or indirectly);
- Using the Licensed Software to manage real assets or facilitate transactions for which you receive compensation;
- Selling, licensing, or distributing the Licensed Software as part of a commercial offering.

Non‑commercial use (e.g., personal testing, academic research) is permitted without a license fee, provided you comply with all other terms.

---

## 4. No Warranty

THE LICENSED SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY ARISING FROM THE USE OF THE LICENSED SOFTWARE.

---

## 5. Enforcement and Termination

The `LicenseRegistry` contract on the blockchain is the sole source of truth for licensed addresses. Any attempt to circumvent the license check (e.g., by removing or bypassing the `onlyLicensed` modifier) automatically voids this license and constitutes a material breach.

Upon breach, your right to use the Licensed Software terminates immediately, and you must cease all commercial use, delete all copies, and destroy any related materials.

---

## 6. Payment

License fees are paid to the architect’s wallet via the `LicenseRegistry` contract. The current fee amount is available by calling `licenseFee()` on that contract. The architect reserves the right to adjust the fee for new licensees; existing licensees are not affected retroactively.

---

## 7. Governing Law

This license shall be governed by and construed in accordance with the laws of [Your Jurisdiction], without regard to its conflict of laws principles.

---

**For inquiries or to obtain a license without using the smart contract, contact the architect directly via GitHub.**
