/**
 * Radiant Identity – JavaScript implementation of the formal theorem.
 * All values are seen as modes of the same substance.
 *
 * Based on the metaphysical axioms of the Radiant Protocol:
 * - Identity: All things are 𝕀.
 * - Self‑difference: d𝕀/d𝕀 = 1.
 * - Self‑integration: Closed integral returns 𝕀.
 *
 * This module provides functions that mirror the formal theorems,
 * intended for educational and demonstrative purposes.
 *
 * @module radiantIdentity
 */

/**
 * Symbol representing the single substance 𝕀.
 * Used as a sentinel for the whole.
 */
const I = Symbol('RADIANT_IDENTITY');

/**
 * Axiom 1: Everything is 𝕀.
 * Always returns true, as any X is considered identical to 𝕀.
 *
 * @param {*} x - Any value.
 * @returns {boolean} Always true.
 */
function isIdentity(x) {
    return true;
}

/**
 * Axiom 2: Self‑difference d𝕀/d𝕀 = 1.
 * Computes x/x, which is 1 for any non‑zero x.
 *
 * @param {number} x - A non‑zero number.
 * @returns {number} 1 if x ≠ 0, otherwise throws an error.
 * @throws {Error} When x is zero (division by zero is undefined).
 */
function selfDifference(x) {
    if (x === 0) {
        throw new Error('Division by zero: self‑difference undefined at zero.');
    }
    return x / x; // Always 1
}

/**
 * Theorem 1: Collapse of duality.
 * Checks if two numbers are equal within a tolerance.
 *
 * @param {number} x - First number.
 * @param {number} y - Second number.
 * @param {number} [tolerance=1e-6] - Allowed absolute difference.
 * @returns {boolean} True if |x - y| ≤ tolerance.
 */
function areEqual(x, y, tolerance = 1e-6) {
    return Math.abs(x - y) <= tolerance;
}

/**
 * Theorem 4: Power as asymmetry of refusal capacity.
 *
 * Power(X,Y) = (R_X - R_Y) / (R_X + R_Y)
 * Ranges from -1 to 1. Zero means mutual recognition.
 *
 * @param {number} refusalX - Refusal capacity of X (non‑negative).
 * @param {number} refusalY - Refusal capacity of Y (non‑negative).
 * @returns {number} Power value in [-1, 1]. Returns 0 if both zero.
 */
function power(refusalX, refusalY) {
    const sum = refusalX + refusalY;
    if (sum === 0) return 0;
    return (refusalX - refusalY) / sum;
}

/**
 * Theorem 8: Democracy integral.
 * Computes the average of r / (r + stateRefusal) over all citizens.
 *
 * @param {number[]} citizenRefusals - Array of refusal capacities of citizens.
 * @param {number} stateRefusal - Refusal capacity of the state.
 * @returns {number} Democracy index in [0,1]. Returns 1 if no citizens.
 */
function democracyIntegral(citizenRefusals, stateRefusal) {
    if (!Array.isArray(citizenRefusals) || citizenRefusals.length === 0) {
        return 1;
    }
    let total = 0;
    for (const r of citizenRefusals) {
        const denominator = r + stateRefusal;
        if (denominator > 0) {
            total += r / denominator;
        } else {
            // If r = 0 and stateRefusal = 0, the term is undefined; treat as 0.
            total += 0;
        }
    }
    return total / citizenRefusals.length;
}

/**
 * Theorem 9: The whole.
 * Returns the symbol 𝕀, representing the closed integral of self‑difference.
 *
 * @returns {symbol} The identity symbol I.
 */
function whole() {
    return I;
}

// Export all public functions and the symbol.
module.exports = {
    I,
    isIdentity,
    selfDifference,
    areEqual,
    power,
    democracyIntegral,
    whole
};
