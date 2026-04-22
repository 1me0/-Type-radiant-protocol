#!/usr/bin/env python3
"""
Recursive Communication Simulation

Simulates a three‑entity system: Reality (R), Self (S), and Other (O).
- R: dynamic ground truth
- S: your internal understanding
- O: listener's understanding

Dynamics:
    R_{t+1} = R_t + ε_R
    E_t = S_t + ε_E
    O_{t+1} = O_t + β (E_t - O_t)
    S_{t+1} = S_t + α (R_{t+1} - S_t) + γ (O_{t+1} - S_t)

Parameters α, β, γ control learning, communication, and feedback rates.

Author: Radiant Protocol
License: MIT
"""

import argparse
import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, List, Dict, Optional
import os
from datetime import datetime


class CommunicationSimulator:
    """
    Recursive communication simulator with order‑invariant updates.
    """

    def __init__(
        self,
        dim: int = 5,
        alpha: float = 0.2,
        beta: float = 0.3,
        gamma: float = 0.1,
        expr_noise_std: float = 0.05,
        reality_noise_std: float = 0.01,
        steps: int = 100,
        seed: Optional[int] = None,
    ):
        """
        Args:
            dim: Dimensionality of the state space.
            alpha: Self's learning rate toward Reality.
            beta: Other's learning rate toward Self's expression.
            gamma: Self's feedback learning rate toward Other.
            expr_noise_std: Standard deviation of expression noise.
            reality_noise_std: Standard deviation of reality drift.
            steps: Number of simulation steps.
            seed: Random seed for reproducibility.
        """
        self.dim = dim
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.expr_noise_std = expr_noise_std
        self.reality_noise_std = reality_noise_std
        self.steps = steps

        self.rng = np.random.default_rng(seed)

        # Initial states
        self.R = self.rng.standard_normal(dim)
        self.S = self.rng.standard_normal(dim)
        self.O = self.rng.standard_normal(dim)

        # History
        self.history: Dict[str, List[float]] = {
            "self_error": [],
            "other_error": [],
            "total_error": [],
            "R_norm": [],
            "S_norm": [],
            "O_norm": [],
        }

    def step(self) -> Tuple[float, float, float]:
        """
        Perform one iteration of the recursive update.

        Returns:
            Tuple of (self_error, other_error, total_error)
        """
        # 1. Dynamic reality (drift)
        self.R += self.rng.normal(0, self.reality_noise_std, self.dim)

        # 2. Noisy expression
        noise = self.rng.normal(0, self.expr_noise_std, self.dim)
        E = self.S + noise

        # 3. Other update
        self.O += self.beta * (E - self.O)

        # 4. Self update (combined: truth + feedback)
        self.S += self.alpha * (self.R - self.S) + self.gamma * (self.O - self.S)

        # Compute errors
        e_self = np.linalg.norm(self.R - self.S)
        e_other = np.linalg.norm(self.S - self.O)
        e_total = e_self + e_other

        # Record
        self.history["self_error"].append(e_self)
        self.history["other_error"].append(e_other)
        self.history["total_error"].append(e_total)
        self.history["R_norm"].append(np.linalg.norm(self.R))
        self.history["S_norm"].append(np.linalg.norm(self.S))
        self.history["O_norm"].append(np.linalg.norm(self.O))

        return e_self, e_other, e_total

    def run(self) -> Dict[str, List[float]]:
        """Run the full simulation and return history."""
        for _ in range(self.steps):
            self.step()
        return self.history

    def plot(self, save_path: Optional[str] = None, show: bool = True) -> None:
        """
        Plot error trajectories.

        Args:
            save_path: If provided, save the figure to this path.
            show: Whether to display the plot.
        """
        plt.figure(figsize=(10, 6))
        plt.plot(self.history["self_error"], label="Self Error ‖R − S‖", linewidth=2)
        plt.plot(self.history["other_error"], label="Other Error ‖S − O‖", linewidth=2)
        plt.plot(self.history["total_error"], label="Total Error", linewidth=2)
        plt.xlabel("Time step")
        plt.ylabel("Error (Euclidean distance)")
        plt.title("Recursive Communication Dynamics (Order‑Invariant)")
        plt.legend()
        plt.grid(True, alpha=0.3)
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"Plot saved to {save_path}")
        if show:
            plt.show()
        else:
            plt.close()

    def print_summary(self) -> None:
        """Print final errors and parameters."""
        print("\n" + "=" * 50)
        print("SIMULATION SUMMARY")
        print("=" * 50)
        print(f"Dimensions: {self.dim}")
        print(f"Steps: {self.steps}")
        print(f"α (truth learning): {self.alpha}")
        print(f"β (communication):   {self.beta}")
        print(f"γ (feedback):        {self.gamma}")
        print(f"Expression noise σ:  {self.expr_noise_std}")
        print(f"Reality noise σ:     {self.reality_noise_std}")
        print("-" * 50)
        print(f"Final Self Error:   {self.history['self_error'][-1]:.4f}")
        print(f"Final Other Error:  {self.history['other_error'][-1]:.4f}")
        print(f"Final Total Error:  {self.history['total_error'][-1]:.4f}")
        print("=" * 50)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recursive communication simulation with truth and feedback."
    )
    parser.add_argument("--dim", type=int, default=5, help="State dimension")
    parser.add_argument("--steps", type=int, default=100, help="Number of simulation steps")
    parser.add_argument("--alpha", type=float, default=0.2, help="Self learning rate toward truth")
    parser.add_argument("--beta", type=float, default=0.3, help="Other learning rate")
    parser.add_argument("--gamma", type=float, default=0.1, help="Feedback learning rate")
    parser.add_argument("--expr-noise", type=float, default=0.05, dest="expr_noise_std", help="Expression noise std")
    parser.add_argument("--reality-noise", type=float, default=0.01, dest="reality_noise_std", help="Reality drift std")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--save-plot", type=str, default=None, help="Save plot to file")
    parser.add_argument("--no-show", action="store_true", help="Do not display plot")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    sim = CommunicationSimulator(
        dim=args.dim,
        alpha=args.alpha,
        beta=args.beta,
        gamma=args.gamma,
        expr_noise_std=args.expr_noise_std,
        reality_noise_std=args.reality_noise_std,
        steps=args.steps,
        seed=args.seed,
    )

    sim.run()
    sim.print_summary()
    sim.plot(save_path=args.save_plot, show=not args.no_show)


if __name__ == "__main__":
    main()
