# Radiant Protocol License (RPL)

**Version 1.0, April 2026**

Copyright (c) 2026 [Your Name / 1me0]

## Terms of Use

1. **Grant of License**  
   Anyone may view, copy, modify, and distribute the software (the “Code”) for any purpose, provided that:
   - A one‑time license fee is paid to the architect’s wallet as specified in the `LicenseRegistry` contract.
   - The fee is paid before any commercial use or before deploying the Code on a public blockchain.

2. **Ownership Presence**  
   Even after the fee is paid, all copies of the Code must retain this license file and a visible attribution to the original author (e.g., in the source code headers or in the user interface).

3. **Commercial Use**  
   Commercial use (including but not limited to running the Code as a service, integrating it into a product that generates revenue, or using it to manage real assets) requires a valid license as described in section 1.

4. **No Warranty**  
   The Code is provided “AS IS”, without warranty of any kind.

5. **Enforcement**  
   The license registry contract on the blockchain is the sole source of truth for licensed addresses. Any attempt to bypass the license check (e.g., by removing the modifier) voids the license and constitutes a breach of this agreement.

## Payment

The license fee is paid by calling `purchaseLicense()` on the `LicenseRegistry` contract deployed at the official address. The fee amount is set by the architect and may change over time.
