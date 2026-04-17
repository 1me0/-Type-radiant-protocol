"""
field_simulation.py

Stochastic field simulation of a predictive coding system with state‑dependent noise,
awareness metric, and survivability kernel. Implements the Radiant Protocol's core
field dynamics as a continuous‑time SDE discretised via Euler–Maruyama.

Author: Radiant Protocol
License: MIT
"""

import os
import argparse
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
from typing import Tuple, List, Optional


# ============================================================
# CONFIGURATION (default values – can be overridden via CLI)
# ============================================================
DEFAULT_CONFIG = {
    "N": 200,                # spatial resolution
    "dx": 0.5,               # spatial step
    "dt": 0.01,              # time step
    "steps": 800,            # number of time steps
    "mode": "fundamental",   # "fundamental" or "emergent"
    "boundary": "neumann",   # "periodic" or "neumann"
    "D_phi": 0.1,            # diffusion of reality field
    "D_hat": 0.1,            # diffusion of prediction field
    "D_chi": 0.2,            # diffusion of awareness field
    "lambda_": 1.0,          # prediction‑reality coupling
    "g": 1.0,                # feedback gain
    "m": 1.0,                # awareness field decay
    "sigma_phi": 0.2,        # noise strength (SDE‑consistent)
    "kernel_radius": 5.0,    # survivability kernel radius
    "divergence_threshold": 1e6,
}


# ============================================================
# OPERATORS
# ============================================================
def laplacian(u: np.ndarray, dx: float, boundary: str) -> np.ndarray:
    """
    Discrete Laplacian with periodic or Neumann (second‑order) boundary conditions.

    Args:
        u: Field values (1D array).
        dx: Spatial step.
        boundary: 'periodic' or 'neumann'.

    Returns:
        Laplacian of u (same shape).
    """
    if boundary == "periodic":
        return (np.roll(u, 1) + np.roll(u, -1) - 2 * u) / dx**2
    elif boundary == "neumann":
        lap = np.zeros_like(u)
        # interior
        lap[1:-1] = (u[:-2] + u[2:] - 2 * u[1:-1]) / dx**2
        # ghost‑point reflection (second‑order)
        lap[0] = (u[1] - u[0]) * 2 / dx**2
        lap[-1] = (u[-2] - u[-1]) * 2 / dx**2
        return lap
    else:
        raise ValueError("boundary must be 'periodic' or 'neumann'")


def distance_to_kernel(state: np.ndarray, radius: float) -> float:
    """
    Distance from the prediction field (represented by its norm) to the survivability kernel,
    here a ball of given radius.

    Args:
        state: Prediction field (1D array).
        radius: Kernel radius.

    Returns:
        Non‑negative distance.
    """
    norm = np.linalg.norm(state)
    return max(0.0, norm - radius)


def awareness(err: float, state: np.ndarray, radius: float, eps: float = 1e-8) -> float:
    """
    Bounded awareness in [0,1].
    High awareness when both prediction error AND distance to kernel are small.
    """
    dist = distance_to_kernel(state, radius)
    inv = 1.0 / (err + dist + eps)
    return np.tanh(inv)


# ============================================================
# INITIALISATION
# ============================================================
def initialize(N: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Create initial fields:
        phi:   sinusoidal reality
        phi_hat: zero prediction
        chi:    zero awareness field
    """
    x = np.linspace(0, 2 * np.pi, N)
    phi = np.sin(x)
    phi_hat = np.zeros(N)
    chi = np.zeros(N)
    return phi, phi_hat, chi


# ============================================================
# DYNAMICS STEP (Euler–Maruyama)
# ============================================================
def step(
    phi: np.ndarray,
    phi_hat: np.ndarray,
    chi: np.ndarray,
    dt: float,
    dx: float,
    boundary: str,
    D_phi: float,
    D_hat: float,
    D_chi: float,
    lambda_: float,
    g: float,
    m: float,
    sigma_phi: float,
    mode: str,
    rng: np.random.Generator,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Perform one Euler–Maruyama step for the coupled fields.

    Returns:
        (phi_next, phi_hat_next, chi_next)
    """
    # Reality noise (Wiener increment)
    noise = sigma_phi * np.sqrt(dt) * rng.normal(size=phi.shape)

    # Reality update
    phi_next = phi + dt * (D_phi * laplacian(phi, dx, boundary) - 0.1 * phi) + noise

    # Prediction update (without chi feedback yet)
    phi_hat_next = phi_hat + dt * (
        D_hat * laplacian(phi_hat, dx, boundary) - lambda_ * (phi_hat - phi)
    )

    if mode == "fundamental":
        # Awareness field update
        chi_next = chi + dt * (
            D_chi * laplacian(chi, dx, boundary) - m**2 * chi + g * (phi - phi_hat)
        )
        # Feedback from awareness to prediction
        phi_hat_next += dt * (g * chi_next)
    else:
        chi_next = chi

    return phi_next, phi_hat_next, chi_next


# ============================================================
# SIMULATION LOOP
# ============================================================
def run_simulation(config: dict, seed: Optional[int] = None) -> dict:
    """
    Run the full simulation with the given configuration.

    Returns a dictionary containing final fields, error history,
    awareness history, and kernel distance history.
    """
    # Set up random generator for reproducibility
    rng = np.random.default_rng(seed)

    phi, phi_hat, chi = initialize(config["N"])
    errors = []
    awareness_vals = []
    distances = []
    divergence_threshold = config["divergence_threshold"]

    with tqdm(total=config["steps"], desc=f"Running ({config['mode']})") as pbar:
        for _ in range(config["steps"]):
            phi, phi_hat, chi = step(
                phi, phi_hat, chi,
                dt=config["dt"],
                dx=config["dx"],
                boundary=config["boundary"],
                D_phi=config["D_phi"],
                D_hat=config["D_hat"],
                D_chi=config["D_chi"],
                lambda_=config["lambda_"],
                g=config["g"],
                m=config["m"],
                sigma_phi=config["sigma_phi"],
                mode=config["mode"],
                rng=rng,
            )

            err = np.linalg.norm(phi - phi_hat)
            if err > divergence_threshold:
                print(f"\n⚠️ Divergence detected: error = {err:.2e} > {divergence_threshold:.2e}. Stopping early.")
                break

            errors.append(err)
            d_kernel = distance_to_kernel(phi_hat, config["kernel_radius"])
            distances.append(d_kernel)
            awareness_vals.append(awareness(err, phi_hat, config["kernel_radius"]))
            pbar.update(1)

    return {
        "phi": phi,
        "phi_hat": phi_hat,
        "chi": chi,
        "errors": np.array(errors),
        "awareness": np.array(awareness_vals),
        "distances": np.array(distances),
    }


# ============================================================
# VISUALISATION
# ============================================================
def plot_results(
    phi: np.ndarray,
    phi_hat: np.ndarray,
    errors: np.ndarray,
    awareness_vals: np.ndarray,
    distances: np.ndarray,
    save_dir: str = ".",
):
    """Generate and save three standard plots."""
    os.makedirs(save_dir, exist_ok=True)

    plt.figure()
    plt.plot(errors)
    plt.title("Error Convergence")
    plt.xlabel("Time step")
    plt.ylabel(r"$||\phi - \hat\phi||$")
    plt.grid()
    plt.savefig(os.path.join(save_dir, "error_convergence.png"), dpi=150)

    plt.figure()
    plt.plot(awareness_vals, label="Awareness (combined)")
    plt.plot(distances, label="Distance to kernel")
    plt.title("Awareness and Kernel Distance")
    plt.xlabel("Time step")
    plt.ylabel("Value")
    plt.legend()
    plt.grid()
    plt.savefig(os.path.join(save_dir, "awareness_and_distance.png"), dpi=150)

    plt.figure()
    plt.plot(phi, label=r"$\phi$ (Reality)")
    plt.plot(phi_hat, label=r"$\hat\phi$ (Prediction)")
    plt.legend()
    plt.title("Final Fields")
    plt.grid()
    plt.savefig(os.path.join(save_dir, "final_fields.png"), dpi=150)

    plt.show()


# ============================================================
# PARAMETER SWEEP
# ============================================================
def sweep_parameter(
    param_name: str,
    values: List[float],
    base_config: dict,
    save_dir: str = "sweep_results",
    seed: Optional[int] = 42,
) -> None:
    """
    Sweep over a parameter ('lambda' or 'g'), run simulations, and save
    final error vs parameter plot.
    """
    os.makedirs(save_dir, exist_ok=True)
    final_errors = []
    param_values_list = []

    for val in tqdm(values, desc=f"Sweeping {param_name}"):
        config = base_config.copy()
        if param_name == "lambda":
            config["lambda_"] = val
        elif param_name == "g":
            config["g"] = val
        else:
            raise ValueError("param_name must be 'lambda' or 'g'")

        results = run_simulation(config, seed=seed)
        errors = results["errors"]
        final_errors.append(errors[-1] if len(errors) > 0 else np.inf)
        param_values_list.append(val)

    # Save data
    data = np.array([param_values_list, final_errors]).T
    save_path = os.path.join(save_dir, f"{param_name}_sweep.npy")
    np.save(save_path, data)
    print(f"Saved sweep data to {save_path}")

    # Plot
    plt.figure()
    plt.plot(param_values_list, final_errors, "o-")
    plt.xlabel(param_name)
    plt.ylabel("Final Error")
    plt.title(f"Parameter Sweep: {param_name}")
    plt.grid(True)
    plt.savefig(os.path.join(save_dir, f"{param_name}_sweep.png"), dpi=150)
    plt.show()


# ============================================================
# COMMAND LINE INTERFACE
# ============================================================
def parse_args():
    parser = argparse.ArgumentParser(description="Radiant Protocol field simulation")
    parser.add_argument("--mode", choices=["fundamental", "emergent"], default="fundamental")
    parser.add_argument("--steps", type=int, default=800)
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--sweep", choices=["lambda", "g"], help="Parameter to sweep")
    parser.add_argument("--sweep_values", nargs="+", type=float, help="Values for sweep (e.g., 0.5 1.0 2.0)")
    parser.add_argument("--no_plot", action="store_true", help="Do not show plots (only save files)")
    return parser.parse_args()


def main():
    args = parse_args()
    config = DEFAULT_CONFIG.copy()
    config["mode"] = args.mode
    config["steps"] = args.steps

    if args.sweep:
        if not args.sweep_values:
            print("Error: --sweep_values required for sweep")
            return
        sweep_parameter(args.sweep, args.sweep_values, config, seed=args.seed)
        return

    # Single simulation
    results = run_simulation(config, seed=args.seed)
    print("\nFinal Error:", results["errors"][-1])
    print("Final Awareness:", results["awareness"][-1])
    print("Final Distance to Kernel:", results["distances"][-1])

    # Save raw data
    np.save("errors.npy", results["errors"])
    np.save("awareness.npy", results["awareness"])
    np.save("distances.npy", results["distances"])

    if not args.no_plot:
        plot_results(
            results["phi"],
            results["phi_hat"],
            results["errors"],
            results["awareness"],
            results["distances"],
        )


if __name__ == "__main__":
    main()
