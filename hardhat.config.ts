import { HardhatUserConfig, task } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import * as dotenv from "dotenv";

dotenv.config();

/**
 * @dev UNIVERSAL DEPLOYMENT TASK
 * Usage:
 *   npx hardhat deploy-token --name "Radiant Share" --symbol "RAD" \
 *     --initial-supply "1000000" --recipient 0x... --network sepolia
 *
 * Optional parameters:
 *   --contract "CustomToken"  (default: "RadiantShares")
 *   --delay 30                (seconds before verification)
 */
task("deploy-token", "Deploys a token and sends initial supply to a specified wallet")
  .addParam("name", "Token name")
  .addParam("symbol", "Token symbol")
  .addParam("initialSupply", "Initial supply in whole tokens (positive integer)")
  .addParam("recipient", "Recipient address")
  .addOptionalParam("contract", "Name of the token contract", "RadiantShares")
  .addOptionalParam("delay", "Seconds to wait before verification", "30")
  .setAction(async (taskArgs, hre) => {
    const { ethers, network } = hre;
    const { name, symbol, initialSupply, recipient, contract, delay } = taskArgs;
    const waitSeconds = parseInt(delay);

    // Validate recipient address
    if (!ethers.isAddress(recipient)) {
      throw new Error(`Invalid recipient address: ${recipient}`);
    }

    // Validate initial supply (positive integer)
    const supplyNum = Number(initialSupply);
    if (!Number.isInteger(supplyNum) || supplyNum <= 0) {
      throw new Error(`Initial supply must be a positive integer, got: ${initialSupply}`);
    }

    console.log(`\n--- Radiant Protocol: Deploying ${contract} (${name}) to ${network.name} ---`);
    const [deployer] = await ethers.getSigners();
    console.log(`Deployer: ${deployer.address}`);

    // 1. Deploy Contract
    const Factory = await ethers.getContractFactory(contract);
    const token = await Factory.deploy(name, symbol);
    await token.waitForDeployment();
    const tokenAddress = await token.getAddress();
    console.log(`✅ Contract deployed at: ${tokenAddress}`);

    // 2. Transfer Supply
    const totalSupply = ethers.parseUnits(initialSupply.toString(), 18);
    console.log(`📦 Transferring ${initialSupply} ${symbol} to recipient...`);
    const tx = await token.transfer(recipient, totalSupply);
    await tx.wait();
    console.log(`✅ Transfer complete. Tx: ${tx.hash}`);

    // 3. Automated Verification (skip on local networks)
    if (network.name !== "hardhat" && network.name !== "localhost") {
      console.log(`⏳ Waiting ${waitSeconds} seconds for block propagation...`);
      await new Promise(resolve => setTimeout(resolve, waitSeconds * 1000));

      try {
        await hre.run("verify:verify", {
          address: tokenAddress,
          constructorArguments: [name, symbol],
        });
        console.log("🔍 Contract verified on Etherscan");
      } catch (err: any) {
        console.warn("⚠️ Verification note:", err.message);
      }
    }
    console.log("--- Deployment Complete ---\n");
  });

/**
 * Hardhat configuration
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
      // EIP‑1559 gas settings (optional)
      gasPrice: "auto",
      maxFeePerGas: process.env.MAX_FEE_PER_GAS ? parseInt(process.env.MAX_FEE_PER_GAS) : undefined,
      maxPriorityFeePerGas: process.env.MAX_PRIORITY_FEE_PER_GAS
        ? parseInt(process.env.MAX_PRIORITY_FEE_PER_GAS)
        : undefined,
    },
    mainnet: {
      url: process.env.MAINNET_RPC_URL || "",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
      gasPrice: "auto",
      maxFeePerGas: process.env.MAX_FEE_PER_GAS ? parseInt(process.env.MAX_FEE_PER_GAS) : undefined,
      maxPriorityFeePerGas: process.env.MAX_PRIORITY_FEE_PER_GAS
        ? parseInt(process.env.MAX_PRIORITY_FEE_PER_GAS)
        : undefined,
    },
    arbitrum: {
      url: process.env.ARBITRUM_RPC_URL || "",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
      gasPrice: "auto",
    },
    optimism: {
      url: process.env.OPTIMISM_RPC_URL || "",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
      gasPrice: "auto",
    },
  },
  etherscan: {
    // Required for the 'verify' task
    apiKey: process.env.ETHERSCAN_API_KEY || "",
  },
};

export default config;
