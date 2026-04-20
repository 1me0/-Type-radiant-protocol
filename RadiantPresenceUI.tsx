import { useState, useEffect, useCallback, useRef } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ethers } from "ethers";

// Helper: deterministic hash (djb2) to generate a score between 0-100
function hashToScore(str: string): number {
  let hash = 5381;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) + hash) + str.charCodeAt(i);
    hash = hash & hash; // keep 32-bit
  }
  return Math.abs(hash % 101);
}

// Expected network configuration (adjust for your deployment)
const EXPECTED_CHAIN_ID = 11155111; // Sepolia testnet
const EXPECTED_CHAIN_NAME = "Sepolia";
// Optional: set your contract address via environment variable
const CONTRACT_ADDRESS = import.meta.env.VITE_RADIANT_CONTRACT_ADDRESS || "";

export default function RadiantPresenceUI() {
  const [wallet, setWallet] = useState<string | null>(null);
  const [presenceData, setPresenceData] = useState<{
    identifier: string;
    firstSeen: number;
    score: number;
    anchored: boolean;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isCorrectNetwork, setIsCorrectNetwork] = useState(true);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const isMounted = useRef(true);

  // Load from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem("radiant_presence");
    if (stored) {
      try {
        const data = JSON.parse(stored);
        setPresenceData(data);
        if (data.identifier) setWallet(data.identifier);
      } catch (e) {
        console.warn("Failed to parse stored presence data");
      }
    }
    return () => {
      isMounted.current = false;
    };
  }, []);

  // Helper to check network
  const checkNetwork = useCallback(async (provider: ethers.BrowserProvider) => {
    const network = await provider.getNetwork();
    const chainId = Number(network.chainId);
    if (chainId !== EXPECTED_CHAIN_ID) {
      setIsCorrectNetwork(false);
      setError(`Please switch to ${EXPECTED_CHAIN_NAME} (chain ID ${EXPECTED_CHAIN_ID}). Current: ${chainId}`);
      return false;
    }
    setIsCorrectNetwork(true);
    setError(null);
    return true;
  }, []);

  // Connect wallet and register presence
  const connectAndRegister = useCallback(async () => {
    if (typeof window.ethereum === "undefined") {
      setError("MetaMask not detected. Please install MetaMask.");
      return;
    }
    setLoading(true);
    setError(null);
    setStatusMessage(null);
    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      await provider.send("eth_requestAccounts", []);
      const isNetOk = await checkNetwork(provider);
      if (!isNetOk) {
        setLoading(false);
        return;
      }
      const signer = await provider.getSigner();
      const address = await signer.getAddress();
      setWallet(address);

      // Check if already registered
      const stored = localStorage.getItem("radiant_presence");
      if (stored) {
        const data = JSON.parse(stored);
        if (data.identifier === address) {
          setPresenceData(data);
          setLoading(false);
          return;
        }
      }

      // New registration
      const score = hashToScore(address);
      const firstSeen = Date.now();
      const newData = {
        identifier: address,
        firstSeen,
        score,
        anchored: false,
      };
      localStorage.setItem("radiant_presence", JSON.stringify(newData));
      setPresenceData(newData);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to connect wallet.");
    } finally {
      if (isMounted.current) setLoading(false);
    }
  }, [checkNetwork]);

  // Disconnect wallet (clear local state)
  const disconnect = useCallback(() => {
    setWallet(null);
    setPresenceData(null);
    localStorage.removeItem("radiant_presence");
    setError(null);
    setStatusMessage(null);
  }, []);

  // On‑chain anchoring (simulated or real)
  const anchorOnChain = useCallback(async () => {
    if (!presenceData || !wallet) {
      setError("No presence data to anchor.");
      return;
    }
    if (!window.ethereum) {
      setError("MetaMask not detected");
      return;
    }
    if (!CONTRACT_ADDRESS) {
      setError("Contract address not configured. Please set VITE_RADIANT_CONTRACT_ADDRESS.");
      return;
    }
    setLoading(true);
    setError(null);
    setStatusMessage("Preparing anchoring...");
    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      const isNetOk = await checkNetwork(provider);
      if (!isNetOk) {
        setLoading(false);
        return;
      }
      const signer = await provider.getSigner();
      // Minimal ABI for registerPresence (adjust to your contract)
      const abi = [
        "function registerPresence(string memory identifier, uint256 score, uint256 timestamp) external",
      ];
      const contract = new ethers.Contract(CONTRACT_ADDRESS, abi, signer);
      setStatusMessage("Sending transaction...");
      const tx = await contract.registerPresence(
        presenceData.identifier,
        presenceData.score,
        presenceData.firstSeen
      );
      setStatusMessage("Waiting for confirmation...");
      await tx.wait();
      const updated = { ...presenceData, anchored: true };
      localStorage.setItem("radiant_presence", JSON.stringify(updated));
      setPresenceData(updated);
      setStatusMessage("✅ Successfully anchored on‑chain!");
      setTimeout(() => setStatusMessage(null), 3000);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Anchoring failed.");
      setStatusMessage(null);
    } finally {
      if (isMounted.current) setLoading(false);
    }
  }, [presenceData, wallet, checkNetwork]);

  const formatDate = (timestamp: number) => new Date(timestamp).toLocaleString();

  // Listen for account/network changes
  useEffect(() => {
    if (typeof window.ethereum !== "undefined") {
      const handleAccountsChanged = (accounts: string[]) => {
        if (accounts.length === 0) {
          disconnect();
        } else if (accounts[0] !== wallet) {
          // Reload presence data for new account
          const stored = localStorage.getItem("radiant_presence");
          if (stored) {
            try {
              const data = JSON.parse(stored);
              if (data.identifier === accounts[0]) {
                setPresenceData(data);
                setWallet(accounts[0]);
              } else {
                disconnect();
              }
            } catch (e) {
              disconnect();
            }
          } else {
            disconnect();
          }
        }
      };
      const handleChainChanged = () => {
        window.location.reload();
      };
      window.ethereum.on("accountsChanged", handleAccountsChanged);
      window.ethereum.on("chainChanged", handleChainChanged);
      return () => {
        window.ethereum.removeListener("accountsChanged", handleAccountsChanged);
        window.ethereum.removeListener("chainChanged", handleChainChanged);
      };
    }
  }, [wallet, disconnect]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-black text-white p-6">
      <Card className="w-full max-w-md rounded-2xl shadow-xl bg-zinc-900 border-zinc-800">
        <CardContent className="p-6 text-center space-y-6">
          <motion.h1
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-2xl font-bold"
          >
            Radiant Presence
          </motion.h1>
          <p className="text-sm opacity-70">
            Prove you were there. Turn it into value.
          </p>

          {error && (
            <div className="p-2 bg-red-900/50 text-red-300 rounded-xl text-sm">
              {error}
            </div>
          )}
          {statusMessage && (
            <div className="p-2 bg-blue-900/50 text-blue-300 rounded-xl text-sm">
              {statusMessage}
            </div>
          )}

          {!presenceData ? (
            <Button onClick={connectAndRegister} disabled={loading} className="w-full">
              {loading ? (
                <>
                  <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></span>
                  Connecting...
                </>
              ) : (
                "Connect Wallet & Register Presence"
              )}
            </Button>
          ) : (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-zinc-800 text-left space-y-2">
                <p><strong>Identifier:</strong> {presenceData.identifier.slice(0,6)}...{presenceData.identifier.slice(-4)}</p>
                <p><strong>Presence Score:</strong> {presenceData.score}/100</p>
                <p><strong>First seen:</strong> {formatDate(presenceData.firstSeen)}</p>
                <p><strong>Anchored on‑chain:</strong> {presenceData.anchored ? "✅ Yes" : "❌ No"}</p>
              </div>

              <div className="flex gap-2">
                {!presenceData.anchored && (
                  <Button onClick={anchorOnChain} disabled={loading} variant="outline" className="flex-1">
                    {loading ? (
                      <>
                        <span className="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></span>
                        Anchoring...
                      </>
                    ) : (
                      "Anchor on‑chain"
                    )}
                  </Button>
                )}
                <Button onClick={disconnect} variant="ghost" className="flex-1" disabled={loading}>
                  Disconnect
                </Button>
              </div>
              {!isCorrectNetwork && (
                <p className="text-xs text-yellow-400">
                  ⚠️ Wrong network. Please switch to {EXPECTED_CHAIN_NAME}.
                </p>
              )}
              {!CONTRACT_ADDRESS && !presenceData.anchored && (
                <p className="text-xs text-yellow-400">
                  ℹ️ Contract address not set. Anchoring is simulated (no on‑chain record).
                </p>
              )}
              <p className="text-xs text-gray-400">
                Your presence score is deterministic and can be used for CIS scoring, staking multipliers, or reputation.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
    }
