import { ethers } from "ethers";
import RadiantSharesABI from "./abis/RadiantShares.json";
import RadiantABI from "./abis/Radiant.json";
import ArchitectFeeABI from "./abis/ArchitectFee.json";
import RegistryABI from "./abis/Registry.json";

// ABI map for all known contracts
const ABI_MAP: Record<string, ethers.InterfaceAbi> = {
  RadiantShares: RadiantSharesABI,
  Radiant: RadiantABI,
  ArchitectFee: ArchitectFeeABI,
  // Add other contracts as needed
};

// Registry address – should be loaded from environment or config
const REGISTRY_ADDRESS = process.env.NEXT_PUBLIC_REGISTRY_ADDRESS || "0x...";

let registryInstance: ethers.Contract | null = null;

function getRegistry(provider: ethers.Provider): ethers.Contract {
  if (!registryInstance) {
    registryInstance = new ethers.Contract(REGISTRY_ADDRESS, RegistryABI, provider);
  }
  return registryInstance;
}

/**
 * Retrieves a contract instance from the canonical Registry.
 * @param contractName Name of the contract (must match ABI_MAP key)
 * @param provider Ethers provider (e.g., BrowserProvider or JsonRpcProvider)
 * @returns ethers.Contract instance
 * @throws Error if contract not registered, address invalid, or ABI missing.
 */
export async function getRadiantContract(
  contractName: string,
  provider: ethers.Provider
): Promise<ethers.Contract> {
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
    console.error(`Failed to fetch contract ${contractName}:`, error);
    throw new Error(`Decoherence Detected: ${contractName} unavailable.`);
  }
}
