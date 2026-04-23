// RadiantDiscovery.ts
// Dynamic contract discovery from the canonical Registry with self‑healing cache.

import { ethers } from "ethers";
import RadiantSharesABI from "./abis/RadiantShares.json";
import RadiantABI from "./abis/Radiant.json";
import ArchitectFeeABI from "./abis/ArchitectFee.json";
import RegistryABI from "./abis/Registry.json";

// ============================================================
// ABI Map
// ============================================================
const ABI_MAP: Record<string, ethers.InterfaceAbi> = {
  RadiantShares: RadiantSharesABI,
  Radiant: RadiantABI,
  ArchitectFee: ArchitectFeeABI,
  // Add other contracts as needed
};

// ============================================================
// Registry Configuration
// ============================================================
const REGISTRY_ADDRESS = process.env.NEXT_PUBLIC_REGISTRY_ADDRESS || "0x...";

// Cache for registry contract instances, keyed by chainId.
const registryCache = new Map<number, ethers.Contract>();

// Active listeners per chainId to avoid duplicates.
const activeListeners = new Map<number, () => void>();

// ============================================================
// Registry Instance Cache
// ============================================================

/**
 * Returns the Registry contract instance for the given provider's chain.
 * Cached per chainId to avoid repeated contract creation.
 *
 * @param provider Ethers provider (e.g., BrowserProvider or JsonRpcProvider)
 * @returns Registry contract instance
 */
async function getRegistry(provider: ethers.Provider): Promise<ethers.Contract> {
  const network = await provider.getNetwork();
  const chainId = Number(network.chainId);

  if (!registryCache.has(chainId)) {
    registryCache.set(chainId, new ethers.Contract(REGISTRY_ADDRESS, RegistryABI, provider));
  }
  return registryCache.get(chainId)!;
}

// ============================================================
// Self‑Healing: Event Listener
// ============================================================

/**
 * Subscribes to the Registry's `AddressSet` events and clears the cache
 * whenever a contract address is updated.
 *
 * @param provider Ethers provider connected to the desired network.
 * @param onUpdate Optional callback invoked after cache is cleared.
 * @returns Unsubscribe function to remove the listener.
 */
export async function listenToRegistryUpdates(
  provider: ethers.Provider,
  onUpdate?: () => void
): Promise<() => void> {
  const network = await provider.getNetwork();
  const chainId = Number(network.chainId);

  // Avoid duplicate listeners for the same chain.
  if (activeListeners.has(chainId)) {
    return activeListeners.get(chainId)!;
  }

  const registry = await getRegistry(provider);

  // Handler for AddressSet events.
  const handleAddressSet = (key: string, oldAddress: string, newAddress: string) => {
    console.log(`🔁 Registry updated: ${key} → ${newAddress}. Clearing cache.`);
    registryCache.delete(chainId);
    if (onUpdate) onUpdate();
  };

  // Subscribe to the event.
  registry.on("AddressSet", handleAddressSet);

  // Create unsubscribe function.
  const unsubscribe = () => {
    registry.off("AddressSet", handleAddressSet);
    activeListeners.delete(chainId);
  };

  activeListeners.set(chainId, unsubscribe);
  return unsubscribe;
}

/**
 * Stops listening for updates on a specific chain (or all chains if no provider given).
 * @param provider Optional provider to identify the chain; if omitted, clears all listeners.
 */
export async function stopListening(provider?: ethers.Provider): Promise<void> {
  if (provider) {
    const network = await provider.getNetwork();
    const chainId = Number(network.chainId);
    const unsubscribe = activeListeners.get(chainId);
    if (unsubscribe) {
      unsubscribe();
      activeListeners.delete(chainId);
    }
  } else {
    // Clear all listeners.
    for (const unsubscribe of activeListeners.values()) {
      unsubscribe();
    }
    activeListeners.clear();
  }
}

// ============================================================
// Public API
// ============================================================

/**
 * Retrieves a read‑only contract instance from the canonical Registry.
 *
 * @param contractName Name of the contract (must match a key in ABI_MAP)
 * @param provider Ethers provider (e.g., BrowserProvider or JsonRpcProvider)
 * @returns ethers.Contract instance (read‑only; signer can be attached later)
 * @throws Error if contract not registered, address invalid, or ABI missing.
 */
export async function getRadiantContract(
  contractName: string,
  provider: ethers.Provider
): Promise<ethers.Contract> {
  if (!contractName || contractName.trim() === "") {
    throw new Error("Contract name cannot be empty");
  }
  if (!provider) {
    throw new Error("Provider is required");
  }

  const registry = await getRegistry(provider);
  const address = await registry.getAddress(contractName);

  if (!ethers.isAddress(address) || address === ethers.ZeroAddress) {
    throw new Error(`Contract "${contractName}" not registered or address is zero.`);
  }

  const abi = ABI_MAP[contractName];
  if (!abi) {
    throw new Error(`ABI for "${contractName}" not found in ABI_MAP.`);
  }

  return new ethers.Contract(address, abi, provider);
}

/**
 * Retrieves a contract instance with a signer attached.
 *
 * @param contractName Name of the contract (must match a key in ABI_MAP)
 * @param signer Ethers signer (e.g., from BrowserProvider.getSigner())
 * @returns ethers.Contract instance with signer for write operations.
 */
export async function getRadiantContractWithSigner(
  contractName: string,
  signer: ethers.Signer
): Promise<ethers.Contract> {
  const provider = signer.provider;
  if (!provider) {
    throw new Error("Signer must have a provider");
  }

  const contract = await getRadiantContract(contractName, provider);
  return contract.connect(signer);
}

/**
 * Clears the registry cache for a specific chain or all chains.
 * @param provider Optional provider to identify the chain; if omitted, clears entire cache.
 */
export async function clearRegistryCache(provider?: ethers.Provider): Promise<void> {
  if (provider) {
    const network = await provider.getNetwork();
    const chainId = Number(network.chainId);
    registryCache.delete(chainId);
  } else {
    registryCache.clear();
  }
}

/**
 * Returns the current registry address being used.
 */
export function getRegistryAddress(): string {
  return REGISTRY_ADDRESS;
}
