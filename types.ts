// types.ts
// Radiant Protocol – Core Type Definitions

/**
 * Represents the verification status of a proof of presence.
 * Used for tracking ZK-proof submissions, CIS scoring, and slashing events.
 */
export interface ProofStatus {
  /** Ethereum address or unique identifier of the user who submitted the proof. */
  user: string;

  /**
   * Current state of the proof in the verification pipeline.
   * - `Pending`: Proof submitted but not yet verified.
   * - `Valid`: Proof successfully verified and accepted.
   * - `Slashed`: Proof was invalid, resulting in a penalty (e.g., loss of stake).
   */
  status: 'Pending' | 'Valid' | 'Slashed';

  /**
   * Optional cryptographic hash of the submitted proof (e.g., keccak256).
   * Useful for on‑chain verification and audit trails.
   */
  hash?: string;

  /**
   * Optional reward (in RAD or other token) earned for a valid proof,
   * or the amount slashed for an invalid one (negative value).
   */
  reward?: string;

  /**
   * Optional timestamp (Unix seconds) when the proof was submitted.
   * Helps track latency and ordering.
   */
  submittedAt?: number;

  /**
   * Optional timestamp when the proof was verified (or slashed).
   */
  verifiedAt?: number;

  /**
   * Optional reference to the on‑chain transaction hash where this proof was recorded.
   */
  txHash?: string;
}

/**
 * Type guard to check if a proof status is final (i.e., not pending).
 */
export function isProofFinal(status: ProofStatus['status']): boolean {
  return status === 'Valid' || status === 'Slashed';
}
