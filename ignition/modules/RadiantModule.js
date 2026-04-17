// ignition/modules/RadiantModule.js
// Hardhat Ignition deployment module for the Radiant contract.

const { buildModule } = require("@nomicfoundation/hardhat-ignition/modules");

/**
 * Deployment module for the Radiant smart contract.
 * @param {object} m - Ignition module builder.
 * @returns {object} Deployed contract instances.
 */
const RadiantModule = buildModule("RadiantModule", (m) => {
  // If the contract constructor requires arguments, you can define them here.
  // Example: const constructorArgs = [m.getParameter("initialOwner")];
  // For a parameterless constructor, pass an empty array.
  const constructorArgs = [];

  // Deploy the Radiant contract
  const radiant = m.contract("Radiant", constructorArgs);

  // Log the deployed address after deployment (Ignition handles this automatically)
  // Return the contract instance so it can be used by other modules or tests.
  return { radiant };
});

module.exports = RadiantModule;
