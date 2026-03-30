import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

const RadiantModule = buildModule("RadiantModule", (m) => {
  const radiant = m.contract("Radiant", []);

  return { radiant };
});

export default RadiantModule;
