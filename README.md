# Radiant Protocol: Proof of Presence via Recursive Zero‑Knowledge Arguments

## Abstract

We introduce Radiant Protocol, a cryptographic system for proving presence—the fact that an entity was actively responsive within a specific time window—without revealing sensitive information. Unlike traditional identity systems, Radiant focuses on liveness-bound participation rather than static identity. The protocol combines digital signatures, blockchain-derived challenges, zero-knowledge proofs, and recursive proof composition (IVC) to produce compact, verifiable attestations of ordered presence events. We formalise the model, define security properties, and analyse adversarial strategies under both cryptographic and economic assumptions.

## 1. Introduction

Modern distributed systems rely heavily on identity and ownership, yet these primitives fail to capture a critical dimension: **presence**. Presence refers to the ability of an entity to act within a constrained time window, demonstrating real‑time responsiveness.

We propose Radiant Protocol, which replaces identity‑based trust with **proof of presence**. The protocol leverages:

- Blockchain‑derived randomness for liveness challenges
- Zero‑knowledge proofs for privacy
- Recursive proof composition for scalability

## 2. Preliminaries

### 2.1 Notation

- $\lambda$: security parameter. For production deployment, we target $\lambda = 128$ bits of security, achievable with the BLS12‑381 curve for the ZK circuit and BLS signatures for aggregation.
- $H$: cryptographic hash function
- $\mathsf{VerifySig}$: signature verification algorithm
- $\mathsf{VerifyMerkle}$: Merkle inclusion verification

### 2.2 Assumptions

- Existential unforgeability of signatures
- Collision resistance of hash functions
- Blockchain satisfies chain quality and unpredictability

## 3. System Model

### 3.1 Presence Event

A **presence event** is a tuple  

\[
e = (u, a, t, \sigma, c, \sigma_c, \pi_s)
\]  

where:  
- $u$ – entity identifier (public key)  
- $a$ – action or statement  
- $t$ – block height  
- $\sigma$ – signature of $(u,a,t)$  
- $c$ – challenge $H(\text{block}_{t-1} \| \text{domain\_sep})$  
- $\sigma_c$ – signature of $c$  
- $\pi_s$ – zero‑knowledge proof of stake $s_u \ge S_{\min}$  

**Privacy note:** The tuple components $c$, $\sigma_c$, and $\pi_s$ are included in the **private witness** of the ZK proof $\pi$, while the verifier only receives the public inputs $(\text{root}_t, \Delta, n, \text{domain\_sep})$.

**Minimum stake:** $S_{\min}$ is a protocol parameter initially set to **1000 RAD** (0.001% of max supply) and adjustable via governance with a 2‑day timelock (as implemented in `RadiantShares.sol`).

### 3.2 Challenge Construction

\[
c = H(\text{block}_{t-1} \,\|\, \text{domain\_sep})
\]

where  

\[
\text{domain\_sep} = \text{"RADIANT\_PRESENCE\_CHALLENGE\_V1"}
\]

to prevent cross‑protocol replay attacks. Bias is bounded by the economic cost of withholding blocks ($\varepsilon_{\text{hash}} + \varepsilon_{\text{MEV}}$).

### 3.3 Response Constraint

\[
t_c \le t \le t_c + \delta
\]

with **slack tolerance** of at most one block to account for propagation delay: the signature time may be up to one block earlier than the final inclusion block.

## 4. Protocol Definition

### 4.1 Prover Algorithm

1. Observe block $\text{block}_{t-1}$.
2. Compute $c$ and sign it.
3. Sign the event $(u,a,t)$.
4. Generate ZK proof $\pi$ of the relation in Section 3.1.
5. Optionally fold $\pi$ into an existing aggregated proof $\Pi_n$.

### 4.2 Verifier Algorithm

Given $\Pi_n$ and public inputs $(\text{root}_t, \Delta, n, \text{domain\_sep})$:

- Verify the recursive proof $\Pi_n$ (constant time).
- The recursive proof $\Pi_n$ **attests** that every challenge $c_i$ was correctly derived from $\text{block}_{t_i-1}$ and that the timestamps are strictly increasing.
- No per‑event verification is performed on‑chain; all checks are inside the ZK circuit.

## 5. Recursive Aggregation

Define  

\[
\Pi_{n+1} = \mathsf{Fold}(\Pi_n, \pi_{n+1})
\]

Properties:

- **Correctness** – if $\Pi_n$ and $\pi_{n+1}$ verify, then $\Pi_{n+1}$ verifies.
- **Compactness** – $|\Pi_{n+1}| = O(1)$, verification $O(1)$.

## 6. Security Model

### 6.1 Completeness  
For any honest entity, a valid proof exists and verifies with probability 1.

### 6.2 Soundness (Game‑Based)  

**Game 1 (Forgery):**  
1. Challenger generates system parameters.  
2. Adversary $\mathcal{A}$ may query presence proofs for chosen events (adaptive).  
3. $\mathcal{A}$ outputs a proof $\Pi_n$ for a sequence **not** in the relation $\mathcal{R}$ (i.e., at least one event invalid, challenge missing, order wrong, or stake insufficient).  
4. $\mathcal{A}$ wins if $\mathsf{Verify}(\Pi_n) = 1$.

The advantage of $\mathcal{A}$ is  

\[
\mathsf{Adv}_{\mathcal{A}}(\lambda) = \left|\Pr[\mathcal{A} \text{ wins}] - \frac{1}{2}\right| \le \mathsf{negl}(\lambda).
\]

### 6.3 Zero‑Knowledge  
For any valid sequence, the proof distribution is computationally indistinguishable from a simulator’s output without access to private witnesses.

## 7. Adversarial Analysis

| Attack | Mitigation |
|--------|-------------|
| Replay | Timestamp + fresh challenge |
| Sybil | Minimum stake (economic) |
| Long‑range | Block‑anchored timestamps |
| Miner bias | Economic cost of withholding blocks |

## 8. Implementation Considerations

- **Signatures:** BLS (Boneh–Lynn–Shacham) for aggregation or ECDSA for Ethereum compatibility.
- **Merkle tree:** Sparse Merkle tree (e.g., using Poseidon hash) as used in Ethereum’s state.
- **ZK circuit:** Use Nova folding scheme [Kothapalli2022] with SNARK‑friendly primitives.
- **On‑chain verification:** The contract receives $\Pi_n$ and verifies it using a pre‑compiled verifier (e.g., via `SnarkVerifier`).

## 9. Conclusion

Radiant introduces a new primitive: **verifiable presence**. It enables trustless systems grounded in real‑time activity rather than static identity. The protocol is scalable, private, and economically secure.

## References

[Kothapalli2022] Kothapalli, A., Setty, S., & Tzialla, I. (2022). Nova: Recursive Zero-Knowledge Arguments from Folding Schemes. *Cryptology ePrint Archive*, Report 2022/1252.  

[BLS2004] Boneh, D., Lynn, B., & Shacham, H. (2004). Short signatures from the Weil pairing. *Journal of Cryptology*, 17(4), 297–319.  

[ETHMerkle] Ethereum Foundation. (2020). “Sparse Merkle Trees”. Ethereum Wiki.

---

**© 2025 Radiant Protocol Contributors**
