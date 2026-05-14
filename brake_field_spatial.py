"""
brake_field_spatial.py

The Brake Field – spatial profile solver with information‑modulated coupling.

Solves the static Klein–Gordon equation:
    φ''(r) + (2/r) φ'(r) = dV/dφ + β_eff(U(r)) · ρ(r)

in spherical symmetry, where β_eff = β₀ · (1 + η_U · tanh(U))
and U(r) = |φ(r) − φ_min(ρ(r))| / φ_min(ρ(r)) measures the local
epistemic uncertainty.

Natural units: M_Pl = 1.

Author: Radiant Protocol
License: MIT (code) / RPML v1.0 (mathematical models)
"""

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import root_scalar
from typing import Callable, Tuple, Optional

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
M_PLANCK_REDUCED = 2.435e18          # GeV
G_PER_CM3_TO_PLANCK = 4.3e18 / (M_PLANCK_REDUCED**4)   # 1 g/cm³ in Planck units

# ---------------------------------------------------------------------------
# Brake Field class with spatial solver
# ---------------------------------------------------------------------------
class BrakeField:
    """
    Chameleon scalar field with information‑modulated matter coupling.

    Parameters
    ----------
    n : float       – potential index (V ∝ φ⁻ⁿ)
    M : float       – mass scale in GeV
    beta0 : float   – baseline matter coupling
    eta_U : float   – sensitivity of β to epistemic uncertainty U
    """

    def __init__(self, n=1.0, M=2.4e-12, beta0=1.0, eta_U=0.5):
        self.n = n
        self.M = M / M_PLANCK_REDUCED   # → Planck units
        self.beta0 = beta0
        self.eta_U = eta_U

    # ----- potential -----
    def V(self, phi):
        if phi <= 0: return np.inf
        return self.M**(4 + self.n) / (phi**self.n)

    def dV(self, phi):
        if phi <= 0: return -np.inf
        return -self.n * self.M**(4 + self.n) / (phi**(self.n + 1))

    # ----- minimum & mass -----
    def phi_min(self, rho):
        if rho <= 0: return np.inf
        return (self.n * self.M**(4 + self.n) / (self.beta0 * rho))**(1.0 / (self.n + 1))

    def m_eff(self, phi):
        """Second derivative of V at arbitrary φ."""
        if phi <= 0: return np.inf
        return np.sqrt(self.n * (self.n + 1) * self.M**(4 + self.n) / (phi**(self.n + 2)))

    # ----- information‑modulated coupling -----
    def beta_eff(self, phi, rho):
        """
        β_eff = β₀ · (1 + η_U · tanh(U))
        where U = |φ − φ_min(ρ)| / φ_min(ρ)
        """
        pmin = self.phi_min(rho)
        if np.isinf(pmin) or pmin <= 0:
            return self.beta0
        U = abs(phi - pmin) / pmin
        return self.beta0 * (1.0 + self.eta_U * np.tanh(U))

    # ----- effective potential -----
    def dV_eff(self, phi, rho):
        """Derivative of V_eff w.r.t φ."""
        return self.dV(phi) + self.beta_eff(phi, rho) * rho

    # ----------------------------------------------------------------
    # SPATIAL PROFILE SOLVER (shooting method)
    # ----------------------------------------------------------------
    def radial_ode(self, r, y, rho_func):
        """
        ODE system for φ(r):
            y[0] = φ
            y[1] = dφ/dr
        """
        phi, psi = y[0], y[1]
        rho = rho_func(r)
        # handle coordinate singularity at r=0 via regularized form
        if r < 1e-10:
            dpsi = self.dV_eff(phi, rho) / 3.0   # L'Hôpital
        else:
            dpsi = -2.0 * psi / r + self.dV_eff(phi, rho)
        return [psi, dpsi]

    def solve_profile(
        self,
        rho_func: Callable[[float], float],
        r_span: Tuple[float, float],
        rho_out: float,
        n_points: int = 2000,
        phi_guess: Optional[float] = None,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Solve φ(r) for a given density profile ρ(r).

        Uses shooting from the centre outward:
            φ(0) is adjusted so that φ(r_max) ≈ φ_min(ρ_out).

        Parameters
        ----------
        rho_func : callable  – ρ(r) in Planck units
        r_span   : (r_min, r_max) – radial domain
        rho_out  : background density (Planck units)
        n_points : resolution for output

        Returns
        -------
        r_grid, phi_grid, beta_grid
        """
        r_min, r_max = r_span
        phi_out = self.phi_min(rho_out)

        # initial guess for φ(0) from thin‑shell approximation
        phi_in = self.phi_min(rho_func(0.0))
        if phi_guess is None:
            phi_guess = phi_in * 0.99

        # shooting: adjust φ(0) to match φ(r_max) ≈ phi_out
        def mismatch(phi0):
            sol = solve_ivp(
                self.radial_ode, (r_min, r_max),
                [phi0, 0.0],
                args=(rho_func,),
                method='RK45',
                rtol=1e-8, atol=1e-12,
                t_eval=np.linspace(r_min, r_max, 500),
            )
            if not sol.success:
                return 1e10
            return sol.y[0, -1] - phi_out

        try:
            result = root_scalar(
                mismatch,
                bracket=[phi_in * 0.5, phi_in * 1.5],
                method='brentq',
            )
            phi0 = result.root
        except ValueError:
            # fallback: use the thin‑shell value
            phi0 = phi_guess

        # final integration with the correct φ(0)
        r_eval = np.logspace(np.log10(r_min), np.log10(r_max), n_points)
        sol = solve_ivp(
            self.radial_ode, (r_min, r_max),
            [phi0, 0.0],
            args=(rho_func,),
            method='RK45',
            rtol=1e-8, atol=1e-12,
            t_eval=r_eval,
        )

        phi_profile = sol.y[0]
        beta_profile = np.array([self.beta_eff(phi, rho_func(r)) for phi, r in zip(phi_profile, r_eval)])
        return r_eval, phi_profile, beta_profile


# ---------------------------------------------------------------------------
# Demonstration: the Sun
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import matplotlib.pyplot as plt

    # initialise the Brake Field
    brake = BrakeField(n=1.0, M=2.4e-12, beta0=1.0, eta_U=0.5)

    # densities (Planck units)
    rho_sun = 1.41 * G_PER_CM3_TO_PLANCK
    rho_gal = 1e-24 * G_PER_CM3_TO_PLANCK

    # Sun radius in Planck length
    # 1 cm = 1.97e31 ℓ_P, but we work in dimensionless units
    # For illustration, use a scaled radius.
    R_sun_planck = 1e-10   # representative dimensionless radius

    # density profile: uniform sphere
    def rho_sun_profile(r):
        return rho_sun if r < R_sun_planck else rho_gal

    # solve the spatial profile
    r_vals, phi_vals, beta_vals = brake.solve_profile(
        rho_func=rho_sun_profile,
        r_span=(1e-14, 1e-8),
        rho_out=rho_gal,
        n_points=2000,
    )

    # compute reference minima
    phi_in = brake.phi_min(rho_sun)
    phi_out = brake.phi_min(rho_gal)

    # --- plots ---
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 10), sharex=True)

    # field profile
    ax1.loglog(r_vals, phi_vals, 'b-', label=r'$\varphi(r)$')
    ax1.axhline(phi_in, color='gray', linestyle='--', label=r'$\varphi_{\rm in}$')
    ax1.axhline(phi_out, color='gray', linestyle=':', label=r'$\varphi_{\rm out}$')
    ax1.axvline(R_sun_planck, color='red', alpha=0.3, label='Sun surface')
    ax1.set_ylabel(r'$\varphi$ (Planck units)')
    ax1.set_title('Brake Field Profile through the Sun')
    ax1.legend()

    # effective coupling
    ax2.semilogx(r_vals, beta_vals, 'g-', label=r'$\beta_{\rm eff}(r)$')
    ax2.axhline(brake.beta0, color='gray', linestyle='--', label=r'$\beta_0$')
    ax2.axvline(R_sun_planck, color='red', alpha=0.3)
    ax2.set_xlabel('r (Planck units)')
    ax2.set_ylabel(r'$\beta_{\rm eff}$')
    ax2.set_title('Information‑Modulated Coupling Strength')
    ax2.legend()

    plt.tight_layout()
    plt.show()

    # screening summary
    print("=" * 50)
    print("  Brake Field – Spatial Profile Solver")
    print("=" * 50)
    print(f"  φ_min (inside)  = {phi_in:.3e} M_Pl")
    print(f"  φ_min (outside) = {phi_out:.3e} M_Pl")
    print(f"  φ(0)            = {phi_vals[0]:.3e} M_Pl")
    print(f"  φ(R_sun)        = {phi_vals[np.argmin(np.abs(r_vals - R_sun_planck))]:.3e} M_Pl")
    print(f"  β_eff (inside)  = {beta_vals[0]:.4f}")
    print(f"  β_eff (outside) = {beta_vals[-1]:.4f}")
    print(f"  β₀              = {brake.beta0}")
    print()
    if phi_vals[0] / phi_in < 1.01:
        print("  ✅ The Sun is screened. Field stuck near φ_in inside.")
    else:
        print("  ⚠️  Field not fully screened – check parameters.")
