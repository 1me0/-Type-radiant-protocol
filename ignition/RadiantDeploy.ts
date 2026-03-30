import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

const RadiantDeploy = buildModule("RadiantDeploy", (m) => {
  const token = m.contract("RadiantShares", []);
  const radiant = m.contract("Radiant", [token]);

  return { token, radiant };
});

export default RadiantDeploy;
npx hardhat ignition deploy ignition/modules/RadiantDeploy.ts --network ganache
npx hardhat ignition deploy ignition/modules/RadiantDeploy.ts --network sepolia
npx hardhat ignition deploy ignition/modules/RadiantDeploy.ts --network sepolia
