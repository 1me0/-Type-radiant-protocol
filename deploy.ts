import { ethers } from "hardhat";

async function main() {
  console.log("🚀 Starting Radiant Protocol Ignition...");

  const Radiant = await ethers.getContractFactory("Radiant");
  const radiant = await Radiant.deploy();

  await radiant.waitForDeployment();

  console.log(`✅ Radiant Protocol anchored at: ${await radiant.getAddress()}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

