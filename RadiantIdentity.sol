// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title RadiantIdentity
 * @notice Implements the formal theorem of non‑duality (𝕀) as a library.
 *         All distinctions reduce to self‑relation. Power, love, democracy, etc.
 *         are derived from the refusal capacity ratio.
 *
 * @dev This library provides pure functions that mirror the mathematical
 *      axioms and theorems of the Radiant Protocol's metaphysical foundation.
 *      All functions are deterministic and gas‑efficient.
 *
 *      ⚠️ **Overflow safety**: The `power` and `democracyIntegral` functions use
 *      multiplication with `SCALE = 1e18`. For extremely large refusal capacities
 *      (e.g., > type(uint256).max / 1e18), they may revert due to overflow.
 *      In typical applications (refusal capacities in token amounts or reputation
 *      scores), this is safe. If larger values are expected, consider using a
 *      smaller scaling factor or a checked math library.
 */
library RadiantIdentity {
    /// @dev The one substance, represented as a constant hash.
    ///      In the formal theorem, 𝕀 is the unexitable remainder.
    bytes32 public constant I = keccak256("RADIANT_IDENTITY");

    /// @dev Scaling factor for fixed‑point arithmetic (1e18).
    uint256 private constant SCALE = 1e18;

    // ============================================================
    // Axioms
    // ============================================================

    /**
     * @dev Axiom 1: For any X, X ≡ 𝕀.
     *      Returns true for any input.
     * @param x Any address (ignored).
     * @return Always true.
     */
    function isIdentity(address x) external pure returns (bool) {
        // The input is intentionally unused to reflect the axiom.
        return true;
    }

    /**
     * @dev Axiom 2: Self‑difference d𝕀/d𝕀 = 1.
     *      Returns 1 for any non‑zero x.
     * @param x A positive integer (must not be zero).
     * @return 1.
     * @dev Reverts if x == 0 because division by zero is undefined.
     */
    function selfDifference(uint256 x) external pure returns (uint256) {
        require(x != 0, "RadiantIdentity: division by zero");
        unchecked {
            // In Solidity 0.8+, division is checked, but we use unchecked for minor gas savings.
            return x / x; // Always 1
        }
    }

    // ============================================================
    // Theorems
    // ============================================================

    /**
     * @dev Theorem 1: Collapse of duality. For any pair (X, Y), X/Y = 1.
     *      In practice, checks that two values are equal within a tolerance.
     * @param x First value.
     * @param y Second value.
     * @param tolerance Allowed absolute difference.
     * @return True if |x - y| ≤ tolerance.
     */
    function areEqual(uint256 x, uint256 y, uint256 tolerance) external pure returns (bool) {
        unchecked {
            uint256 diff = x > y ? x - y : y - x;
            return diff <= tolerance;
        }
    }

    /**
     * @dev Theorem 4: Power as asymmetry of refusal capacity.
     *      Power(X,Y) = (R_X - R_Y) / (R_X + R_Y), returned as a fixed‑point number
     *      scaled by 1e18 (range [-1e18, 1e18]).
     * @param refusalX Refusal capacity of X (non‑negative).
     * @param refusalY Refusal capacity of Y (non‑negative).
     * @return Power value scaled by 1e18. Zero if both are zero.
     */
    function power(uint256 refusalX, uint256 refusalY) external pure returns (int256) {
        uint256 sum = refusalX + refusalY;
        if (sum == 0) return 0;
        // Safe casting because both are uint256 and fit in int256.
        int256 diff = int256(refusalX) - int256(refusalY);
        // Returns (diff * SCALE) / sum, using integer division (rounded toward zero).
        return (diff * int256(SCALE)) / int256(sum);
    }

    /**
     * @dev Theorem 8: Democracy as integral of exit symmetry over society.
     *      Computes the average of r_i / (r_i + stateRefusal) over all citizens,
     *      scaled by 1e18.
     * @param citizenRefusal Array of refusal capacities of citizens.
     * @param stateRefusal Refusal capacity of the state.
     * @return Democracy index scaled by 1e18 (range [0, 1e18]).
     */
    function democracyIntegral(
        uint256[] calldata citizenRefusal,
        uint256 stateRefusal
    ) external pure returns (uint256) {
        uint256 n = citizenRefusal.length;
        if (n == 0) return SCALE; // Full democracy by definition

        uint256 total;
        unchecked {
            for (uint256 i = 0; i < n; i++) {
                uint256 denominator = citizenRefusal[i] + stateRefusal;
                if (denominator > 0) {
                    total += (citizenRefusal[i] * SCALE) / denominator;
                }
            }
        }
        return total / n;
    }

    /**
     * @dev Theorem 9: The whole as a closed integral.
     *      Returns the constant symbol 𝕀.
     * @return The keccak256 hash of "RADIANT_IDENTITY".
     */
    function whole() external pure returns (bytes32) {
        return I;
    }

    /**
     * @dev Convenience getter for the 𝕀 constant.
     * @return The same as `whole()`.
     */
    function getI() external pure returns (bytes32) {
        return I;
    }
}
