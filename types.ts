/**
 * RADIANT PROTOCOL: CORE PRIMITIVES
 * These types govern the transition from Action to Awareness.
 */

export type Presence = {
  actor_id: string;    // The Identity (S)
  timestamp: number;   // The Time (Real-time integral)
  context: string;     // The Mind (M) - What happened?
  signature: string;   // The Proof (F) - Verification
};

export type Proof = {
  presence_hash: string;
  validation_sources: string[]; // Minimum 2 (Art. 2)
  consensus_score: number;      // 0.0 -> 1.0 (Art. 3)
};

export type Value = {
  proof_id: string;
  weight: number;               // The w(t) coefficient
  utility: number;              // The kinetic potential (RAD)
};

export type Meaning = {
  value: Value;
  interpretation: string;       // The final distillation (Awareness)
};

export type Vector = {
  name: "alpha" | "beta" | "gamma";
  action: () => any;
  weight: number;
};
