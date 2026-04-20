// RadiantDiscovery.ts
// Dynamic contract discovery from the canonical Registry.

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

// Simple cache for registry contract instances (keyed by provider URL/chain ID)
const registryCache = new Map<string, ethers.Contract>();

/**
 * Returns the Registry contract instance, caching per provider.
 * @param provider Ethers provider (e.g., BrowserProvider or JsonRpcProvider)
 * @returns Registry contract instance
 */
function getRegistry(provider: ethers.Provider): ethers.Contract {
  // Use a unique key: chain ID + provider's connection URL (if available)
  // For simplicity, we use a combination of chainId and a hash of the provider.
  // In practice, you could also just create a new instance each time – overhead is negligible.
  let key: string;
  if (typeof (provider as any)._getConnection === "function") {
    key = `${provider._getConnection().url}_${provider._network?.chainId ?? ""}`;
  } else {
    key = `${provider.constructor.name}_${Date.now()}`;
  }
  if (!registryCache.has(key)) {
    registryCache.set(key, new ethers.Contract(REGISTRY_ADDRESS, RegistryABI, provider));
  }
  return registryCache.get(key)!;
}

/**
 * Retrieves a contract instance from the canonical Registry.
 * @param contractName Name of the contract (must match ABI_MAP key)
 * @param provider Ethers provider (e.g., BrowserProvider or JsonRpcProvider)
 * @returns ethers.Contract instance (read‑only; signer can be attached later)
 * @throws Error if contract not registered, address invalid, or ABI missing.
 */
export async function getRadiantContract(
  contractName: string,
  provider: ethers.Provider
): Promise<ethers.Contract> {
  try {
    // Validate inputs
    if (!contractName || contractName.trim() === "") {
      throw new Error("Contract name cannot be empty");
    }
    if (!provider) {
      throw new Error("Provider is required");
    }

    const registry = getRegistry(provider);
    const address = await registry.getAddress(contractName);

    if (!ethers.isAddress(address) || address === ethers.ZeroAddress) {
      throw new Error(`Contract "${contractName}" not registered or address is zero.`);
    }

    const abi = ABI_MAP[contractName];
    if (!abi) {
      throw new Error(`ABI for "${contractName}" not found in ABI_MAP.`);
    }

    // Return a read‑only contract (no signer). The caller can connect a signer if needed.
    return new ethers.Contract(address, abi, provider);
  } catch (error) {
    console.error(`Failed to fetch contract ${contractName}:`, error);
    throw new Error(`Contract discovery failed: ${contractName} unavailable.`);
  }
}

/**
 * Clears the registry cache (useful when switching networks).
 */
export function clearRegistryCache(): void {
  registryCache.clear();
}
