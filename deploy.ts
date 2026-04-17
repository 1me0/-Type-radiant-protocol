// deploy.ts
// Hardhat deployment script for Radiant Protocol smart contracts.
// Supports network detection, contract verification, and constructor arguments.

import { ethers, run, network } from "hardhat";

/**
 * Deploys a contract with optional constructor arguments and waits for confirmation.
 * Optionally verifies the contract on Etherscan if not on a local network.
 */
async function deployContract(
  contractName: string,
  args: any[] = [],
  verify: boolean = true,
  verificationDelay: number = 60000 // 60 seconds
) {
  console.log(`\n📡 Deploying ${contractName} to ${network.name}...`);
  const factory = await ethers.getContractFactory(contractName);
  const contract = await factory.deploy(...args);
  await contract.waitForDeployment();
  const address = await contract.getAddress();
  console.log(`✅ ${contractName} deployed at: ${address}`);

  // Optional verification on Etherscan (skip for local networks)
  if (verify && network.name !== "hardhat" && network.name !== "localhost") {
    console.log(`⏳ Waiting ${verificationDelay / 1000} seconds before verification...`);
    await new Promise(resolve => setTimeout(resolve, verificationDelay));
    try {
      await run("verify:verify", {
        address: address,
        constructorArguments: args,
      });
      console.log("🔍 Contract verified on Etherscan");
    } catch (err: any) {
      if (err.message.includes("Already Verified")) {
        console.log("ℹ️ Contract already verified");
      } else {
        console.warn("⚠️ Verification failed:", err.message);
      }
    }
  }

  return { contract, address };
}

async function main() {
  console.log("🚀 Starting Radiant Protocol deployment...");

  // Example: Deploy the Radiant token contract (adjust constructor args as needed)
  // If your contract has no constructor arguments, pass an empty array.
  const contractName = "Radiant"; // Change to your actual contract name
  const constructorArgs: any[] = []; // e.g., ["TokenName", "TKN", deployerAddress]

  const { address } = await deployContract(contractName, constructorArgs, true);

  console.log(`\n✨ Deployment complete. Contract address: ${address}`);
}

main().catch((error) => {
  console.error("\n❌ Deployment failed:", error);
  process.exitCode = 1;
});
