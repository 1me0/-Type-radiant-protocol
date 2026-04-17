// ignition/modules/RadiantDeploy.ts
// Hardhat Ignition deployment module for the Radiant Protocol.
// Deploys both the token contract (RadiantShares) and the main Radiant contract,
// passing the token address to the Radiant constructor.

import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

/**
 * Deployment module for RadiantShares and Radiant contracts.
 * 
 * @param m - Ignition module builder.
 * @returns Object containing deployed token and radiant contract instances.
 */
const RadiantDeploy = buildModule("RadiantDeploy", (m) => {
  // Deploy the token contract (RadiantShares) – assumes a parameterless constructor.
  // If the token contract requires constructor arguments, add them here.
  const token = m.contract("RadiantShares", []);

  // Deploy the main Radiant contract, passing the token address as its constructor argument.
  const radiant = m.contract("Radiant", [token]);

  // Return the deployed instances for use in other modules or tests.
  return { token, radiant };
});

export default RadiantDeploy;
