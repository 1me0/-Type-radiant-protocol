# Threat Model & Defense Blueprint

The Radiant Protocol is built on the principle that **perfect defense contains the blueprint of perfect attack**. This document outlines potential attack vectors and how the system’s design anticipates and mitigates them – not by hiding the blueprint, but by making attack economically irrational.

## Attack Vectors & Countermeasures

| Attack Vector | Defense Mechanism | Why It Contains the Blueprint |
|---------------|-------------------|-------------------------------|
| **Sybil / fake proofs** | ZK‑recursive proofs (Nova) + staking requirement | The proof system requires computational work; staking adds economic cost. Attackers know the exact cost to forge a proof – it exceeds any reward. |
| **Censorship / front‑running** | Decentralized relayers + WebSocket broadcast + council emergency override | The design assumes adversarial mempools; the council can pause or revert malicious actions. The blueprint of a front‑run is the same as a legitimate fast confirmation. |
| **Fee avoidance** | Built‑in transfer fee (50% to architect) + `ArchitectFeeV2` contract | Any token transfer that bypasses the fee contract would require modifying the ERC20 standard – which is impossible. The attack would require a fork, which is outside the threat model. |
| **Long‑range attack on staking** | Reward per token accounting + time‑locked vesting | The blueprint is a reorg; but staking rewards are calculated on the current chain state. A reorg would need to overturn finality, which is infeasible on Ethereum L2. |
| **Council collusion** | Multi‑sig requirement (2‑of‑3) + 100% court agreement for removal | The council’s own rules require unanimity for major changes. The blueprint of a rogue council is the same as a legitimate council – the difference is transparency and on‑chain voting. |
| **Vault key compromise** | AES‑256‑GCM with time‑locked 5‑day approval | The encryption is standard; the time lock gives the architect 5 days to rotate keys. The attack blueprint is a stolen key – but the time lock makes it useless without approval. |

## Conclusion

Every defense mechanism in Radiant is built by first understanding how an attacker would think. The code does not rely on obscurity; it relies on alignment, cost, and transparency. This file serves as the explicit blueprint – the map of attack that the defense already contains.
