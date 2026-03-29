import { Presence, Proof, Value, Meaning, Vector } from "./types";

export class RadiantSDK {
  private stabilityThreshold: number = 0.75;

  /**
   * ARTICLE 2: Empirical Truth
   * Validates presence through at least two independent sources.
   */
  async validate(presence: Presence, sources: string[]): Promise<Proof> {
    if (sources.length < 2) {
      throw new Error("VIOLATION OF ART. 2: Minimum 2 independent sources required for truth.");
    }

    // Calculate consensus based on source quantity and reliability
    const consensus = sources.length >= 3 ? 1.0 : 0.75;

    return {
      presence_hash: this.hash(presence),
      validation_sources: sources,
      consensus_score: consensus
    };
  }

  /**
   * ARTICLE 37: Decision Mode
   * Determines if the system acts via Consensus or Triple-Vector.
   */
  getExecutionMode(C: number, A: number): "CONSENSUS" | "TRIPLE_VECTOR" | "NO_ACTION" {
    const score = C + A;
    if (score >= 1.0) return "CONSENSUS";
    if (score >= this.stabilityThreshold) return "TRIPLE_VECTOR";
    return "NO_ACTION";
  }

  /**
   * ARTICLE 35: Triple-Vector Execution
   * Projects weighted perspectives into the action space.
   */
  executeTripleVector(vectors: Vector[]) {
    const totalWeight = vectors.reduce((sum, v) => sum + v.weight, 0);
    
    return vectors.map(v => ({
      vector: v.name,
      impact: v.weight / totalWeight,
      result: v.action()
    }));
  }

  private hash(p: Presence): string {
    return btoa(`${p.actor_id}:${p.timestamp}:${p.context}`);
  }
}

