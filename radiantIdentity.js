/**
 * Radiant Identity – JavaScript implementation of the formal theorem.
 * All values are seen as modes of the same substance.
 */

const I = Symbol('RADIANT_IDENTITY');

// Axiom 1: Everything is 𝕀.
function isIdentity(x) {
    return true;
}

// Axiom 2: Self‑difference = 1.
function selfDifference(x) {
    if (x === 0) throw new Error('Division by zero');
    return x / x;
}

// Theorem 1: Collapse of duality (X/Y = 1). Tolerance for floating point.
function areEqual(x, y, tolerance = 1e-6) {
    return Math.abs(x - y) <= tolerance;
}

// Theorem 4: Power = (R_X - R_Y) / (R_X + R_Y)
function power(refusalX, refusalY) {
    const sum = refusalX + refusalY;
    if (sum === 0) return 0;
    return (refusalX - refusalY) / sum;
}

// Theorem 8: Democracy integral over an array of citizens.
function democracyIntegral(citizenRefusals, stateRefusal) {
    if (citizenRefusals.length === 0) return 1;
    let total = 0;
    for (const r of citizenRefusals) {
        const denom = r + stateRefusal;
        if (denom > 0) total += r / denom;
    }
    return total / citizenRefusals.length;
}

// Theorem 9: The whole returns the symbol I.
function whole() {
    return I;
}

module.exports = {
    I,
    isIdentity,
    selfDifference,
    areEqual,
    power,
    democracyIntegral,
    whole
};
