import { HardhatUserConfig, task } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import * as dotenv from "dotenv";

dotenv.config();

// ============================================================
// Helper: ensure required environment variables exist
// ============================================================
function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing environment variable: ${name}`);
  }
  return value;
}

// ============================================================
// DEPLOYMENT TASKS
// ============================================================

/**
 * Deploys a standard ERC20 token with constructor (name, symbol)
 * and transfers initial supply to a recipient.
 * Usage:
 *   npx hardhat deploy-token --name "Radiant Share" --symbol "RAD" \
 *     --initial-supply 1000000 --recipient 0x... --network sepolia
 */
task("deploy-token", "Deploys a token and sends initial supply to a specified wallet")
  .addParam("name", "Token name")
  .addParam("symbol", "Token symbol")
  .addParam("initialSupply", "Initial supply in whole tokens (positive integer)")
  .addParam("recipient", "Recipient address")
  .addOptionalParam("contract", "Name of the token contract", "RadiantShares")
  .addOptionalParam("delay", "Seconds to wait before verification", "30")
  .setAction(async (taskArgs, hre) => {
    const { ethers, network, run } = hre;
    const { name, symbol, initialSupply, recipient, contract, delay } = taskArgs;
    const waitSeconds = parseInt(delay);

    if (!ethers.isAddress(recipient)) {
      throw new Error(`Invalid recipient address: ${recipient}`);
    }
    const supplyNum = Number(initialSupply);
    if (!Number.isInteger(supplyNum) || supplyNum <= 0) {
      throw new Error(`Initial supply must be a positive integer, got: ${initialSupply}`);
    }

    console.log(`\n--- Deploying ${contract} (${name}) to ${network.name} ---`);
    const [deployer] = await ethers.getSigners();
    console.log(`Deployer: ${deployer.address}`);

    const Factory = await ethers.getContractFactory(contract);
    const token = await Factory.deploy(name, symbol);
    await token.waitForDeployment();
    const tokenAddress = await token.getAddress();
    console.log(`✅ Contract deployed at: ${tokenAddress}`);

    const totalSupply = ethers.parseUnits(initialSupply.toString(), 18);
    console.log(`📦 Transferring ${initialSupply} ${symbol} to recipient...`);
    const tx = await token.transfer(recipient, totalSupply);
    await tx.wait();
    console.log(`✅ Transfer complete. Tx: ${tx.hash}`);

    if (network.name !== "hardhat" && network.name !== "localhost") {
      console.log(`⏳ Waiting ${waitSeconds} seconds for block propagation...`);
      await new Promise(resolve => setTimeout(resolve, waitSeconds * 1000));
      try {
        await run("verify:verify", {
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
 * Deploys RadiantSharesUltimate (with architect and treasury wallets).
 * Usage:
 *   npx hardhat deploy-ultimate --name "Radiant Share" --symbol "RAD" \
 *     --architect 0x... --treasury 0x... --network sepolia
 */
task("deploy-ultimate", "Deploys RadiantSharesUltimate with architect and treasury wallets")
  .addParam("name", "Token name")
  .addParam("symbol", "Token symbol")
  .addParam("architect", "Architect wallet address")
  .addParam("treasury", "Protocol treasury address")
  .addOptionalParam("delay", "Seconds to wait before verification", "30")
  .setAction(async (taskArgs, hre) => {
    const { ethers, network, run } = hre;
    const { name, symbol, architect, treasury, delay } = taskArgs;
    const waitSeconds = parseInt(delay);

    if (!ethers.isAddress(architect)) throw new Error(`Invalid architect address: ${architect}`);
    if (!ethers.isAddress(treasury)) throw new Error(`Invalid treasury address: ${treasury}`);

    console.log(`\n--- Deploying RadiantSharesUltimate (${name}) to ${network.name} ---`);
    const [deployer] = await ethers.getSigners();
    console.log(`Deployer: ${deployer.address}`);
    console.log(`Architect: ${architect}`);
    console.log(`Treasury: ${treasury}`);

    const Factory = await ethers.getContractFactory("RadiantSharesUltimate");
    const token = await Factory.deploy(name, symbol, architect, treasury);
    await token.waitForDeployment();
    const tokenAddress = await token.getAddress();
    console.log(`✅ Contract deployed at: ${tokenAddress}`);

    if (network.name !== "hardhat" && network.name !== "localhost") {
      console.log(`⏳ Waiting ${waitSeconds} seconds for block propagation...`);
      await new Promise(resolve => setTimeout(resolve, waitSeconds * 1000));
      try {
        await run("verify:verify", {
          address: tokenAddress,
          constructorArguments: [name, symbol, architect, treasury],
        });
        console.log("🔍 Contract verified on Etherscan");
      } catch (err: any) {
        console.warn("⚠️ Verification note:", err.message);
      }
    }
    console.log("--- Deployment Complete ---\n");
  });

// ============================================================
// Hardhat Configuration
// ============================================================
const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.19",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
      viaIR: true, // optional: improves gas for complex contracts
    },
  },
  networks: {
    // Sepolia testnet
    sepolia: {
      url: process.env.SEPOLIA_RPC_URL || "",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
      gasPrice: "auto",
      maxFeePerGas: process.env.MAX_FEE_PER_GAS ? parseInt(process.env.MAX_FEE_PER_GAS) : undefined,
      maxPriorityFeePerGas: process.env.MAX_PRIORITY_FEE_PER_GAS
        ? parseInt(process.env.MAX_PRIORITY_FEE_PER_GAS)
        : undefined,
    },
    // Ethereum mainnet
    mainnet: {
      url: process.env.MAINNET_RPC_URL || "",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
      gasPrice: "auto",
      maxFeePerGas: process.env.MAX_FEE_PER_GAS ? parseInt(process.env.MAX_FEE_PER_GAS) : undefined,
      maxPriorityFeePerGas: process.env.MAX_PRIORITY_FEE_PER_GAS
        ? parseInt(process.env.MAX_PRIORITY_FEE_PER_GAS)
        : undefined,
    },
    // Arbitrum One
    arbitrum: {
      url: process.env.ARBITRUM_RPC_URL || "",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
      gasPrice: "auto",
      // Arbitrum uses a different fee model; these are optional
      maxFeePerGas: process.env.ARBITRUM_MAX_FEE_PER_GAS
        ? parseInt(process.env.ARBITRUM_MAX_FEE_PER_GAS)
        : undefined,
      maxPriorityFeePerGas: process.env.ARBITRUM_MAX_PRIORITY_FEE_PER_GAS
        ? parseInt(process.env.ARBITRUM_MAX_PRIORITY_FEE_PER_GAS)
        : undefined,
    },
    // Optimism
    optimism: {
      url: process.env.OPTIMISM_RPC_URL || "",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
      gasPrice: "auto",
      maxFeePerGas: process.env.OPTIMISM_MAX_FEE_PER_GAS
        ? parseInt(process.env.OPTIMISM_MAX_FEE_PER_GAS)
        : undefined,
      maxPriorityFeePerGas: process.env.OPTIMISM_MAX_PRIORITY_FEE_PER_GAS
        ? parseInt(process.env.OPTIMISM_MAX_PRIORITY_FEE_PER_GAS)
        : undefined,
    },
    // Local Hardhat node
    hardhat: {
      chainId: 31337,
      mining: {
        auto: true,
        interval: 0,
      },
    },
    // Local Ganache (optional)
    ganache: {
      url: "http://localhost:8545",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
      chainId: 1337,
    },
  },
  etherscan: {
    apiKey: process.env.ETHERSCAN_API_KEY || "",
    // For Arbitrum/Optimism, Etherscan uses different URLs; you can add custom apiKey for each chain
    customChains: [
      {
        network: "arbitrum",
        chainId: 42161,
        urls: {
          apiURL: "https://api.arbiscan.io/api",
          browserURL: "https://arbiscan.io",
        },
      },
      {
        network: "optimism",
        chainId: 10,
        urls: {
          apiURL: "https://api-optimistic.etherscan.io/api",
          browserURL: "https://optimistic.etherscan.io",
        },
      },
    ],
  },
  sourcify: {
    enabled: true, // optional: verify on Sourcify as well
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts",
  },
  mocha: {
    timeout: 60000,
  },
};

export default config;
