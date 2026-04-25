"""
cognitive_architecture.py

Full implementation of the Radiant Cognitive Loop – a reality‑grounded,
memory‑aware, goal‑driven engine for structured cognition.

Core meta‑formula:

    C_t = Select_π ∘ Filter_τ ∘ P( A_t × ( O(A_t) ∪ E_t ∪ F ), M_t )

with update:
    A_{t+1} = Update(C_t, M_t)
    M_{t+1} = MemoryUpdate(M_t, C_t)

Mathematical models covered by the Radiant Protocol Master Formula License (RPML) v1.0.

Author: Radiant Protocol
License: MIT (software) / RPML v1.0 (mathematical models)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import (
    Generic, TypeVar, Set, FrozenSet, Dict, List, Any, Union,
    Tuple, Optional, Callable, Iterator
)
import numpy as np

# ---------------------------------------------------------------------------
# Generic type variables
# ---------------------------------------------------------------------------
A = TypeVar("A", bound=object)  # Awareness state
D = TypeVar("D", bound=object)  # Sensory data
F = TypeVar("F", bound=object)  # Formal symbol


# ---------------------------------------------------------------------------
# Abstract Components
# ---------------------------------------------------------------------------

class Observation(ABC, Generic[A, D]):
    """Observation function O : A → D (internal self‑perception)."""
    @abstractmethod
    def observe(self, awareness: A) -> D:
        ...


class Environment(ABC, Generic[D]):
    """External environment that provides sensory samples E_t."""
    @abstractmethod
    def sample(self) -> D:
        ...


class FormalSystem(Generic[F]):
    """Immutable set of formal symbols F."""
    def __init__(self, symbols: FrozenSet[F]) -> None:
        self._symbols = symbols if isinstance(symbols, frozenset) else frozenset(symbols)

    @property
    def symbols(self) -> FrozenSet[F]:
        return self._symbols

    def contains(self, symbol: F) -> bool:
        return symbol in self._symbols

    def __repr__(self) -> str:
        return f"FormalSystem({sorted(self._symbols)})"


class StructuredProcessing(ABC, Generic[A, D, F]):
    """
    Structured processing P : A × (D ∪ F) → A.
    Given awareness and an input (sensory or formal), returns a new awareness state.
    In the loop, P also receives current memory M_t.
    """
    @abstractmethod
    def process(self, awareness: A, input_: Union[D, F], memory: 'Memory[A]') -> A:
        ...


class Constraint(ABC, Generic[A]):
    """Truth filter: evaluates a state and returns a score in [0,1]."""
    @abstractmethod
    def evaluate(self, state: A) -> float:
        ...


class Evaluator(ABC, Generic[A]):
    """Multi‑faceted evaluation: semantic (coherence), factual (grounding), pragmatic (usefulness)."""
    @abstractmethod
    def semantic(self, state: A) -> float:
        ...
    @abstractmethod
    def factual(self, state: A) -> float:
        ...
    @abstractmethod
    def pragmatic(self, state: A) -> float:
        ...

    def combined(self, state: A,
                 w_sem: float = 0.4, w_fact: float = 0.4, w_prag: float = 0.2) -> float:
        return w_sem * self.semantic(state) + w_fact * self.factual(state) + w_prag * self.pragmatic(state)


class Objective(ABC, Generic[A]):
    """Goal‑driven value: a scalar that the system tries to maximise."""
    @abstractmethod
    def value(self, state: A) -> float:
        ...


class Policy(ABC, Generic[A]):
    """Selection policy π: chooses which states to keep from a weighted field."""
    @abstractmethod
    def select(self, awareness_field: Dict[A, float]) -> List[A]:
        ...


class Memory(ABC, Generic[A]):
    """A temporal store that accumulates and retrieves past states."""
    @abstractmethod
    def store(self, state: A, score: float) -> None:
        ...
    @abstractmethod
    def retrieve_relevant(self, k: int = 5) -> List[A]:
        ...
    @abstractmethod
    def all_states(self) -> Set[A]:
        ...


# ---------------------------------------------------------------------------
# Awareness Field (dynamic, weighted)
# ---------------------------------------------------------------------------

class AwarenessField(Generic[A]):
    """A dynamic set of awareness states with associated weights (importance)."""
    def __init__(self, initial_states: Dict[A, float]):
        self._states: Dict[A, float] = {s: w for s, w in initial_states.items()}

    def update(self, new_states: Dict[A, float], memory: Memory[A]) -> None:
        """
        Update the field: keep top weighted states from current + new_states.
        New weight = old_weight * relevance * truth (here combined externally).
        This is where the cognitive system decides what to attend to.
        """
        # Merge new states with current ones, adding weights
        for s, w in new_states.items():
            self._states[s] = self._states.get(s, 0.0) + w

        # Remove states with extremely low weight to prevent explosion
        self._states = {s: w for s, w in self._states.items() if w > 0.01}

    def top_k(self, k: int) -> List[A]:
        """Return states with highest weights."""
        sorted_items = sorted(self._states.items(), key=lambda x: x[1], reverse=True)
        return [s for s, _ in sorted_items[:k]]

    def as_dict(self) -> Dict[A, float]:
        return dict(self._states)

    def __len__(self) -> int:
        return len(self._states)


# ---------------------------------------------------------------------------
# Cognitive Loop (the main engine)
# ---------------------------------------------------------------------------

class CognitiveLoop(Generic[A, D, F]):
    """
    The complete interactive cognitive cycle:
        C_t = Select_π ∘ Filter_τ ∘ P( A_t × ( O(A_t) ∪ E_t ∪ F ), M_t )
    with updates to awareness and memory.
    """
    def __init__(
        self,
        awareness_field: AwarenessField[A],
        observation: Observation[A, D],
        environment: Environment[D],
        formal_system: FormalSystem[F],
        processing: StructuredProcessing[A, D, F],
        constraint: Constraint[A],
        evaluator: Evaluator[A],
        objective: Objective[A],
        policy: Policy[A],
        memory: Memory[A],
        constraint_threshold: float = 0.5,
        top_k_candidates: int = 10,
    ):
        self.awareness = awareness_field
        self.observation = observation
        self.environment = environment
        self.formal = formal_system
        self.processing = processing
        self.constraint = constraint
        self.evaluator = evaluator
        self.objective = objective
        self.policy = policy
        self.memory = memory
        self.constraint_threshold = constraint_threshold
        self.top_k_candidates = top_k_candidates

    def step(self) -> None:
        """Execute one cognitive cycle t → t+1."""
        # 1. Generate input set: internal observation, external sample, formal symbols
        internal_samples: Set[D] = {self.observation.observe(a) for a in self.awareness.top_k(self.top_k_candidates)}
        external_sample: Set[D] = {self.environment.sample()}
        inputs = internal_samples.union(external_sample).union(self.formal.symbols)

        # 2. Process all selected awareness states with each input → candidates
        candidates: Dict[A, float] = {}
        selected_aware = self.policy.select(self.awareness.as_dict())
        for a in selected_aware:
            for i in inputs:
                # Processing depends on memory and awareness
                new_state = self.processing.process(a, i, self.memory)

                # 3. Filter by constraint (truth threshold)
                if self.constraint.evaluate(new_state) < self.constraint_threshold:
                    continue

                # 4. Evaluate overall quality: combine evaluator and objective
                eval_score = self.evaluator.combined(new_state)
                obj_value = self.objective.value(new_state)
                final_score = 0.6 * eval_score + 0.4 * obj_value  # balanced

                candidates[new_state] = candidates.get(new_state, 0.0) + final_score

        # 5. Update memory with the computed scores
        for state, score in candidates.items():
            self.memory.store(state, score)

        # 6. Update awareness field with new candidates
        self.awareness.update(candidates, self.memory)

    def run(self, steps: int, verbose: bool = False) -> None:
        for t in range(steps):
            self.step()
            if verbose:
                print(f"Step {t}: awareness size = {len(self.awareness)}, "
                      f"top state = {self.awareness.top_k(1)[0] if self.awareness else None}")


# ---------------------------------------------------------------------------
# Concrete Example: Embedding‑based Cognitive Loop
# ---------------------------------------------------------------------------

class EmbeddingAwareness:
    """Awareness state as an embedding vector (immutable, hashable)."""
    __slots__ = ("_vector",)

    def __init__(self, vector: np.ndarray) -> None:
        if not isinstance(vector, np.ndarray):
            vector = np.asarray(vector, dtype=np.float64)
        if vector.ndim != 1:
            raise ValueError("Vector must be 1‑D")
        self._vector: Tuple[float, ...] = tuple(vector.tolist())

    @property
    def vector(self) -> np.ndarray:
        return np.array(self._vector, dtype=np.float64)

    @property
    def dimension(self) -> int:
        return len(self._vector)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EmbeddingAwareness):
            return NotImplemented
        return self._vector == other._vector

    def __hash__(self) -> int:
        return hash(self._vector)

    def __repr__(self) -> str:
        vec_repr = ", ".join(f"{v:.2f}" for v in self._vector[:4])
        return f"Emb([{vec_repr}])"


class SimpleObservation(Observation[EmbeddingAwareness, np.ndarray]):
    def observe(self, a: EmbeddingAwareness) -> np.ndarray:
        return a.vector.copy()


class NoisyEnvironment(Environment[np.ndarray]):
    """A simple environment producing random noise vectors."""
    def __init__(self, dim: int, noise_std: float = 0.1):
        self.dim = dim
        self.noise_std = noise_std

    def sample(self) -> np.ndarray:
        return np.random.randn(self.dim) * self.noise_std


class AdditiveProcessing(StructuredProcessing[EmbeddingAwareness, np.ndarray, str]):
    """Add sensory data or apply formal operations; influenced by memory (e.g., retrieval‑based addition)."""
    def process(self, awareness: EmbeddingAwareness, input_: Union[np.ndarray, str], memory: Memory[EmbeddingAwareness]) -> EmbeddingAwareness:
        vec = awareness.vector.copy()
        if isinstance(input_, np.ndarray):
            vec += input_
            return EmbeddingAwareness(vec)
        elif isinstance(input_, str):
            if input_ == "normalize":
                norm = np.linalg.norm(vec)
                return EmbeddingAwareness(vec / norm) if norm > 1e-12 else awareness
            elif input_ == "scale_half":
                return EmbeddingAwareness(vec * 0.5)
            elif input_ == "shift_positive":
                return EmbeddingAwareness(np.maximum(vec, 0.0))
            else:
                raise ValueError(f"Unknown formal symbol {input_}")
        raise TypeError


class NormConstraint(Constraint[EmbeddingAwareness]):
    """Truth filter: states must have a normalized norm (e.g., not too large, not zero)."""
    def __init__(self, min_norm: float = 0.01, max_norm: float = 5.0):
        self.min_norm = min_norm
        self.max_norm = max_norm

    def evaluate(self, state: EmbeddingAwareness) -> float:
        norm = np.linalg.norm(state.vector)
        if self.min_norm <= norm <= self.max_norm:
            return 1.0
        else:
            return 0.0


class SimpleEvaluator(Evaluator[EmbeddingAwareness]):
    """Semantic: cosine similarity to unit direction; factual: dot with a factual anchor; pragmatic: norm."""
    def __init__(self, anchor: np.ndarray):
        self.anchor = anchor / np.linalg.norm(anchor)

    def semantic(self, state: EmbeddingAwareness) -> float:
        v = state.vector
        norm = np.linalg.norm(v)
        if norm < 1e-12:
            return 0.0
        return float(np.dot(v / norm, self.anchor))

    def factual(self, state: EmbeddingAwareness) -> float:
        # Example: how close to another "truth" vector
        truth_vec = np.array([1.0, 0.0, 0.0])
        return float(np.dot(state.vector, truth_vec) / (1 + np.linalg.norm(state.vector)))

    def pragmatic(self, state: EmbeddingAwareness) -> float:
        return float(np.linalg.norm(state.vector))  # larger = more actionable


class SumObjective(Objective[EmbeddingAwareness]):
    """Example objective: maximize sum of first two coordinates."""
    def value(self, state: EmbeddingAwareness) -> float:
        v = state.vector
        return float(v[0] + v[1])


class TopKPolicy(Policy[EmbeddingAwareness]):
    def __init__(self, k: int = 3):
        self.k = k
    def select(self, awareness_field: Dict[EmbeddingAwareness, float]) -> List[EmbeddingAwareness]:
        sorted_items = sorted(awareness_field.items(), key=lambda x: x[1], reverse=True)
        return [s for s, _ in sorted_items[:self.k]]


class SimpleMemory(Memory[EmbeddingAwareness]):
    def __init__(self, capacity: int = 100):
        self._store: Dict[EmbeddingAwareness, float] = {}
        self.capacity = capacity

    def store(self, state: EmbeddingAwareness, score: float) -> None:
        self._store[state] = self._store.get(state, 0.0) + score
        # Keep only top capacity
        if len(self._store) > self.capacity:
            sorted_items = sorted(self._store.items(), key=lambda x: x[1], reverse=True)
            self._store = dict(sorted_items[:self.capacity])

    def retrieve_relevant(self, k: int = 5) -> List[EmbeddingAwareness]:
        sorted_items = sorted(self._store.items(), key=lambda x: x[1], reverse=True)
        return [s for s, _ in sorted_items[:k]]

    def all_states(self) -> Set[EmbeddingAwareness]:
        return set(self._store.keys())


# ---------------------------------------------------------------------------
# Demonstration
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    rng = np.random.default_rng(42)
    np.random.seed(42)

    # Create initial awareness field with equal weights
    initial = {
        EmbeddingAwareness(np.array([1.0, 0.0, 0.0])): 1.0,
        EmbeddingAwareness(np.array([0.0, 2.0, 0.0])): 1.0,
        EmbeddingAwareness(np.array([0.5, 0.5, 1.0])): 1.0,
    }
    awareness = AwarenessField(initial)

    obs = SimpleObservation()
    env = NoisyEnvironment(dim=3, noise_std=0.05)
    formal = FormalSystem(frozenset(["normalize", "scale_half", "shift_positive"]))
    proc = AdditiveProcessing()

    constraint = NormConstraint(min_norm=0.01, max_norm=5.0)
    evaluator = SimpleEvaluator(anchor=np.array([1.0, 0.0, 0.0]))
    objective = SumObjective()
    policy = TopKPolicy(k=3)
    memory = SimpleMemory(capacity=50)

    loop = CognitiveLoop(
        awareness_field=awareness,
        observation=obs,
        environment=env,
        formal_system=formal,
        processing=proc,
        constraint=constraint,
        evaluator=evaluator,
        objective=objective,
        policy=policy,
        memory=memory,
        constraint_threshold=0.5,
        top_k_candidates=3,
    )

    print("Running cognitive loop for 5 steps...\n")
    for step in range(5):
        loop.step()
        print(f"After step {step+1}:")
        print(f"  Awareness size: {len(awareness)}")
        top_states = awareness.top_k(3)
        for s in top_states:
            print(f"    {s} weight={awareness.as_dict()[s]:.3f}")
        print(f"  Memory size: {len(memory.all_states())}")
        print()
