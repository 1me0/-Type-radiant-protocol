import { HardhatUserConfig, task } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import * as dotenv from "dotenv";

// Load environment variables from .env file
dotenv.config();

/**
 * @dev UNIVERSAL DEPLOYMENT TASK
 * Use: npx hardhat deploy-token --name "Radiant Share" --symbol "RAD" --initial-supply "1000000" --recipient 0x... --network sepolia
 */
task("deploy-token", "Deploys a token and sends initial supply to a specified wallet")
  .addParam("name", "Token name")
  .addParam("symbol", "Token symbol")
  .addParam("initialSupply", "Initial supply in whole tokens")
  .addParam("recipient", "Recipient address")
  .addOptionalParam("delay", "Seconds to wait before verification", "30")
  .setAction(async (taskArgs, hre) => {
    const { ethers, network } = hre;
    const { name, symbol, initialSupply, recipient, delay } = taskArgs;
    const waitSeconds = parseInt(delay);

    if (!ethers.isAddress(recipient)) throw new Error("Invalid recipient address");

    console.log(`\n--- Radiant Protocol: Manifesting ${name} ---`);
    const [deployer] = await ethers.getSigners();
    console.log(`Deploying with: ${deployer.address}`);

    // 1. Deploy Contract
    const Factory = await ethers.getContractFactory("RadiantShares");
    const token = await Factory.deploy(name, symbol);
    await token.waitForDeployment();
    const tokenAddress = await token.getAddress();
    console.log(`Success: Token anchored at ${tokenAddress}`);

    // 2. Transfer Supply
    const totalSupply = ethers.parseUnits(initialSupply.toString(), 18);
    console.log(`Transferring ${initialSupply} ${symbol} to recipient...`);
    const tx = await token.transfer(recipient, totalSupply);
    await tx.wait();

    // 3. Automated Verification
    if (network.name !== "hardhat" && network.name !== "localhost") {
      console.log(`Waiting ${waitSeconds}s for Etherscan propagation...`);
      await new Promise(resolve => setTimeout(resolve, waitSeconds * 1000));

      try {
        await hre.run("verify:verify", {
          address: tokenAddress,
          constructorArguments: [name, symbol],
        });
        console.log("Integrity Verified: Contract source is now public.");
      } catch (err: any) {
        console.warn("Verification Note:", err.message);
      }
    }
    console.log("--- Deployment Complete ---\n");
  });

/**
 * @type import('hardhat/config').HardhatUserConfig
 */
const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.19",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },
  networks: {
    sepolia: {
      url: process.env.SEPOLIA_RPC_URL || "",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
    },
    // Add mainnet configuration here when ready for Genesis
  },
  etherscan: {
    // Required for the 'verify' task to work
    apiKey: process.env.ETHERSCAN_API_KEY || "",
  },
};

export default config;
