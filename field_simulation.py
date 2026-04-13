import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import os

# ============================================================
# CONFIGURATION
# ============================================================

N = 200
dx = 0.5
dt = 0.01
steps = 800

MODE = "fundamental"   # "emergent" or "fundamental"
BOUNDARY = "neumann"   # "periodic" or "neumann"

# Diffusion
D_phi = 0.1
D_hat = 0.1
D_chi = 0.2

# Coupling
lambda_ = 1.0
g = 1.0
m = 1.0

# Noise (SDE-consistent)
sigma_phi = 0.2

# Survivability kernel (simple ball of radius R)
KERNEL_RADIUS = 5.0

# ============================================================
# OPERATORS
# ============================================================

def laplacian(u):
    """Discrete Laplacian with proper scaling and improved Neumann BC."""
    if BOUNDARY == "periodic":
        return (np.roll(u, 1) + np.roll(u, -1) - 2*u) / dx**2

    elif BOUNDARY == "neumann":
        lap = np.zeros_like(u)

        # interior
        lap[1:-1] = (u[:-2] + u[2:] - 2*u[1:-1]) / dx**2

        # ghost-point reflection (second-order)
        lap[0] = (u[1] - u[0]) * 2 / dx**2
        lap[-1] = (u[-2] - u[-1]) * 2 / dx**2

        return lap

# ============================================================
# DISTANCE TO KERNEL (convex ball)
# ============================================================

def distance_to_kernel(state, radius=KERNEL_RADIUS):
    """Distance from state to the survivability kernel (ball of given radius)."""
    norm = np.linalg.norm(state)
    if norm <= radius:
        return 0.0
    return norm - radius

# ============================================================
# AWARENESS (bounded, combines error and kernel distance)
# ============================================================

def awareness(err, state, eps=1e-8):
    """
    Bounded awareness in [0,1].
    High awareness when both prediction error AND distance to kernel are small.
    """
    dist = distance_to_kernel(state)
    inv = 1.0 / (err + dist + eps)
    return np.tanh(inv)

# ============================================================
# INITIALIZATION
# ============================================================

def initialize():
    x = np.linspace(0, 2*np.pi, N)
    phi = np.sin(x)
    phi_hat = np.zeros(N)
    chi = np.zeros(N)
    return phi, phi_hat, chi

# ============================================================
# STEP FUNCTION (Euler–Maruyama consistent)
# ============================================================

def step(phi, phi_hat, chi):
    # --- stochastic reality ---
    noise = sigma_phi * np.sqrt(dt) * np.random.randn(N)

    phi_next = phi + dt * (
        D_phi * laplacian(phi)
        - 0.1 * phi
    ) + noise

    # --- prediction ---
    phi_hat_next = phi_hat + dt * (
        D_hat * laplacian(phi_hat)
        - lambda_ * (phi_hat - phi)
    )

    # --- awareness field ---
    if MODE == "fundamental":
        chi_next = chi + dt * (
            D_chi * laplacian(chi)
            - m**2 * chi
            + g * (phi - phi_hat)
        )

        phi_hat_next += dt * (g * chi_next)

    else:
        chi_next = chi

    return phi_next, phi_hat_next, chi_next

# ============================================================
# SIMULATION WITH DIVERGENCE CHECK
# ============================================================

def run_simulation(divergence_threshold=1e6):
    phi, phi_hat, chi = initialize()

    errors = []
    awareness_vals = []
    distances_to_kernel = []

    for _ in tqdm(range(steps), desc=f"Running ({MODE})"):
        phi, phi_hat, chi = step(phi, phi_hat, chi)

        err = np.linalg.norm(phi - phi_hat)
        if err > divergence_threshold:
            print(f"\n⚠️ Divergence detected: error = {err:.2e} > {divergence_threshold:.2e}. Stopping early.")
            break

        errors.append(err)
        d_kernel = distance_to_kernel(phi_hat)
        distances_to_kernel.append(d_kernel)
        awareness_vals.append(awareness(err, phi_hat))

    return phi, phi_hat, chi, errors, awareness_vals, distances_to_kernel

# ============================================================
# PARAMETER SWEEP WITH VISUALISATION AND SAVING
# ============================================================

def sweep_parameter(param_name, values, save_dir="sweep_results"):
    """
    Sweep over a parameter (e.g., 'lambda' or 'g').
    Saves final error vs parameter plot and data.
    """
    global lambda_, g
    os.makedirs(save_dir, exist_ok=True)

    final_errors = []
    param_values_list = []

    for val in tqdm(values, desc=f"Sweeping {param_name}"):
        if param_name == "lambda":
            lambda_ = val
        elif param_name == "g":
            g = val
        else:
            raise ValueError("param_name must be 'lambda' or 'g'")

        _, _, _, errors, _, _ = run_simulation()
        final_errors.append(errors[-1] if errors else np.inf)
        param_values_list.append(val)

    # Save data
    data = np.array([param_values_list, final_errors]).T
    save_path = os.path.join(save_dir, f"{param_name}_sweep.npy")
    np.save(save_path, data)
    print(f"Saved sweep data to {save_path}")

    # Plot
    plt.figure()
    plt.plot(param_values_list, final_errors, 'o-')
    plt.xlabel(param_name)
    plt.ylabel("Final Error")
    plt.title(f"Parameter Sweep: {param_name}")
    plt.grid(True)
    plt.savefig(os.path.join(save_dir, f"{param_name}_sweep.png"), dpi=150)
    plt.show()

# ============================================================
# VISUALIZATION
# ============================================================

def plot_results(phi, phi_hat, errors, awareness_vals, distances_to_kernel):
    plt.figure()
    plt.plot(errors)
    plt.title(f"Error Convergence ({MODE})")
    plt.xlabel("Time step")
    plt.ylabel("||φ - φ̂||")
    plt.grid()
    plt.savefig("error_convergence.png", dpi=150)

    plt.figure()
    plt.plot(awareness_vals, label="Awareness (combined)")
    plt.plot(distances_to_kernel, label="Distance to kernel")
    plt.title("Awareness and Kernel Distance")
    plt.xlabel("Time step")
    plt.ylabel("Value")
    plt.legend()
    plt.grid()
    plt.savefig("awareness_and_distance.png", dpi=150)

    plt.figure()
    plt.plot(phi, label="φ (Reality)")
    plt.plot(phi_hat, label="φ̂ (Prediction)")
    plt.legend()
    plt.title("Final Fields")
    plt.grid()
    plt.savefig("final_fields.png", dpi=150)

    plt.show()

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    # Single run
    phi, phi_hat, chi, errors, awareness_vals, distances = run_simulation()

    print("\nFinal Error:", errors[-1])
    print("Final Awareness:", awareness_vals[-1])
    print("Final Distance to Kernel:", distances[-1])

    # Save results from this run
    np.save("errors.npy", errors)
    np.save("awareness.npy", awareness_vals)
    np.save("distances.npy", distances)

    plot_results(phi, phi_hat, errors, awareness_vals, distances)

    # Example parameter sweep (uncomment to run)
    # values = [0.5, 1.0, 2.0]
    # sweep_parameter("g", values)
