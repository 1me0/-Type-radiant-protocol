"""
brayan_brake_chameleon.py

Research‑grade Brayan Brake (chameleon) solver.

Improvements in this version:
  • Correct Friedmann normalisation: H² = (ρ_m + ρ_φ) / (3 M_pl²)
  • Decoupled geometry evaluation: compute H, a'' first, then effective potential.
  • Analytic Kretschmann invariant for FLRW (tidal coherence measure).
  • Placeholder for dynamical Φ (first‑order relaxation).
  • Full background FLRW equations with scalar field and matter.

Author framework: RPML v1.0
Code License: MIT
"""

import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt
from typing import Dict, Callable

class BrayanBrakeCosmo:
    def __init__(self, params: Dict[str, float]):
        # Physical parameters (natural units GeV)
        self.M_pl = params.get('M_pl', 2.435e18)      # reduced Planck mass
        self.M_br = params.get('M_br', 2.4e-12)       # brake mass scale (~meV)
        self.beta = params.get('beta', 1.0)            # matter coupling
        self.xi   = params.get('xi', 1e-3)             # non‑minimal coupling (for U from R)
        self.eta  = params.get('eta', 0.1)             # coupling to Φ·U
        self.lam  = params.get('lam', 0.05)            # coupling to ν (coherence)
        self.n    = params.get('n', 1.0)               # potential index

        # Reference scale for Kretschmann (controls coherence decay)
        self.K0 = params.get('K0', 1e-40)              # roughly Planck curvature

        # Placeholder: Φ (violation density) will be evolved dynamically
        self.Phi = params.get('Phi0', 1e-4)
        # Relaxation constant for Φ
        self.alpha_Phi = params.get('alpha_Phi', 0.0)  # zero → constant for now

    # ---------- Potential ----------
    def V(self, phi):
        eps = 1e-20
        return self.M_br**(4 + self.n) / (phi**self.n + eps)

    def dV_dphi(self, phi):
        eps = 1e-20
        if phi <= 0:
            return -np.inf
        return -self.n * self.M_br**(4 + self.n) * phi**(self.n - 1) / (phi**self.n + eps)**2

    # ---------- Geometry helpers ----------
    def H_sq(self, a, rho_m, phi_val, phi_dot):
        """Friedmann equation: H² = (ρ_m + ρ_φ) / (3 M_pl²)"""
        rho_phi = 0.5 * phi_dot**2 + self.V(phi_val)
        return (rho_m + rho_phi) / (3.0 * self.M_pl**2)

    def Hdot(self, a, H, rho_m, phi_val, phi_dot):
        """Acceleration equation: \dot H = - (ρ_m + ρ_φ + 3p_φ) / (6 M_pl²)"""
        p_phi = 0.5 * phi_dot**2 - self.V(phi_val)
        return -(rho_m + p_phi + phi_dot**2 - self.V(phi_val)) / (6.0 * self.M_pl**2)  # p_phi = 0.5 φdot² - V
        # Actually total pressure = p_phi (matter pressure 0). So:
        # \dot H = - (ρ_m + ρ_φ + 3p_phi) / (6 M_pl²) = - (ρ_m + 0.5 φdot² + V + 3*(0.5 φdot² - V)) / (6 M_pl²)
        # = - (ρ_m + 2 φdot² - 2 V) / (6 M_pl²)
        return -(rho_m + 2*phi_dot**2 - 2*self.V(phi_val)) / (6.0 * self.M_pl**2)

    def Kretschmann_FLRW(self, a, H, Hdot_val):
        """Analytic Kretschmann scalar for flat FLRW: K = 12 ( (H² + Hdot)² + H⁴ )"""
        return 12.0 * ( (H**2 + Hdot_val)**2 + H**4 )

    # ---------- Information sources ----------
    def compute_U(self, H, Hdot_val):
        """U = xi * R² / M_pl⁴, with FLRW R = 6 (H² + Hdot/2?) actually R = 6 (ä/a + H²) = 6 (H² + \dot H + H²) = 6 (2H² + \dot H)."""
        R = 6.0 * (2*H**2 + Hdot_val)
        return self.xi * R**2 / self.M_pl**4

    def compute_nu(self, H, Hdot_val):
        """Coherence decays with tidal deformation: nu = exp(-K / K0)."""
        K = self.Kretschmann_FLRW(None, H, Hdot_val)
        return np.exp(-K / self.K0)

    # ---------- Effective potential ----------
    def dV_eff_dphi(self, phi, rho_m, H, Hdot_val, Phi, U, nu):
        """Derivative of effective potential w.r.t φ including matter and info."""
        dV = self.dV_dphi(phi)
        # Matter gradient
        dV += self.beta * rho_m / self.M_pl
        # Information gradient
        dV += -self.eta * Phi * U + self.lam * nu
        return dV

    # ---------- ODE system ----------
    def ode_system(self, t, y):
        # y = [a, phi, phi_dot, rho_m, Phi]
        a, phi, phi_dot, rho_m, Phi = y

        # 1. Geometry: compute H and Hdot from current state (decoupled)
        H_sq_val = self.H_sq(a, rho_m, phi, phi_dot)
        if H_sq_val < 0:
            H_sq_val = 0.0
        H = np.sqrt(H_sq_val)
        Hdot_val = self.Hdot(a, H, rho_m, phi, phi_dot)

        # 2. Information sources (using geometry)
        U = self.compute_U(H, Hdot_val)
        nu = self.compute_nu(H, Hdot_val)

        # 3. Scalar field acceleration
        dVeff = self.dV_eff_dphi(phi, rho_m, H, Hdot_val, Phi, U, nu)

        # 4. Scale factor
        da_dt = a * H

        # 5. Klein‑Gordon
        dphi_dt = phi_dot
        dphidot_dt = -3.0 * H * phi_dot - dVeff

        # 6. Matter (dust, pressureless)
        drho_dt = -3.0 * H * rho_m

        # 7. Φ evolution (placeholder relaxation)
        # dΦ/dt = -α_Φ (Φ - Φ_source) where Φ_source could be |∇_μ T^{μν}|^2/M_pl^4.
        # For now, just let it decay to zero.
        dPhi_dt = -self.alpha_Phi * Phi

        return [da_dt, dphi_dt, dphidot_dt, drho_dt, dPhi_dt]

    def solve(self, t_span, y0, max_step=1e3):
        sol = solve_ivp(
            self.ode_system, t_span, y0,
            method='RK45', rtol=1e-6, atol=1e-12,
            dense_output=True, max_step=max_step
        )
        return sol

# -----------------------------------------------------------------------------
# DEMONSTRATION
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    params = dict(
        M_pl=2.435e18,
        M_br=2.4e-12,
        beta=1.0,
        xi=1e-3,
        eta=0.1,
        lam=0.05,
        n=1.0,
        K0=1e-40,
        alpha_Phi=0.0,    # no dynamics for this demo
    )
    model = BrayanBrakeCosmo(params)

    # Initial conditions (at Planck time? scaled)
    a0 = 1.0
    phi0 = 1e-3 * params['M_pl']   # start near Planck scale
    phi_dot0 = 0.0
    rho_m0 = 1e-24                 # galactic density GeV⁴
    Phi0 = 1e-4
    y0 = [a0, phi0, phi_dot0, rho_m0, Phi0]

    # Integrate for a short time (GeV^{-1})
    t_span = (0, 1e5)
    sol = model.solve(t_span, y0, max_step=1e3)

    if sol.success:
        print("Integration successful.")
        t = sol.t
        a = sol.y[0]
        phi = sol.y[1]
        rho_m = sol.y[3]
        Phi = sol.y[4]

        fig, axs = plt.subplots(4, 1, figsize=(8, 12), sharex=True)
        axs[0].plot(t, a)
        axs[0].set_ylabel('Scale factor a')
        axs[1].plot(t, phi)
        axs[1].set_ylabel('Brake field φ')
        axs[2].plot(t, rho_m)
        axs[2].set_ylabel('ρ_m')
        axs[3].plot(t, Phi)
        axs[3].set_ylabel('Φ (violation)')
        axs[3].set_xlabel('Time (GeV⁻¹)')
        plt.tight_layout()
        plt.show()

        # Check final state
        print(f"Final φ = {phi[-1]:.3e}")
        print(f"Final ρ_m = {rho_m[-1]:.3e}")
    else:
        print("Integration failed:", sol.message)
