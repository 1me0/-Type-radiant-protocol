import { ethers } from "ethers";

// Assume you have registry address and ABI defined elsewhere
const registryAddress = "0x...";
const registryABI = []; // Registry ABI
const ABI_MAP = {
  RadiantShares: [],
  Radiant: [],
  ArchitectFee: [],
  // ... other contracts
};

let registry: ethers.Contract | null = null;

function getRegistry(provider: ethers.Provider): ethers.Contract {
  if (!registry) {
    registry = new ethers.Contract(registryAddress, registryABI, provider);
  }
  return registry;
}

export async function getRadiantContract(contractName: string, provider: ethers.Provider) {
  try {
    const registry = getRegistry(provider);
    const address = await registry.getAddress(contractName);
    if (!ethers.isAddress(address) || address === ethers.ZeroAddress) {
      throw new Error(`Contract "${contractName}" not registered or invalid address.`);
    }

    const abi = ABI_MAP[contractName];
    if (!abi) {
      throw new Error(`ABI for "${contractName}" not found.`);
    }
    return new ethers.Contract(address, abi, provider);
  } catch (error) {
    console.error(`Failed to fetch contract ${contractName}: `, error);
    throw new Error(`Decoherence Detected: ${contractName} unavailable.`);
  }
}
