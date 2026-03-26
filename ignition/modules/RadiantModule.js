const { buildModule } = require("@nomicfoundation/hardhat-ignition/modules");

// The Master Formula applied to the initial supply
const INITIAL_SUPPLY = 1000000n; // 1 Million RAD

module.exports = buildModule("RadiantModule", (m) => {
  const radiant = m.contract("RadiantToken", [INITIAL_SUPPLY]);

  return { radiant };
});

