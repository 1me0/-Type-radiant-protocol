import { useState, useEffect } from "react";
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

  // Load from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem("radiant_presence");
    if (stored) {
      const data = JSON.parse(stored);
      setPresenceData(data);
      if (data.identifier) setWallet(data.identifier);
    }
  }, []);

  // Helper to check network
  const checkNetwork = async (provider: ethers.BrowserProvider) => {
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
  };

  // Connect wallet and register presence
  const connectAndRegister = async () => {
    if (typeof window.ethereum === "undefined") {
      setError("MetaMask not detected. Please install MetaMask.");
      return;
    }
    setLoading(true);
    setError(null);
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
      setLoading(false);
    }
  };

  // Disconnect wallet (clear local state)
  const disconnect = () => {
    setWallet(null);
    setPresenceData(null);
    localStorage.removeItem("radiant_presence");
    setError(null);
  };

  // Simulate on‑chain anchoring (replace with actual contract call)
  const anchorOnChain = async () => {
    if (!presenceData || !wallet) return;
    if (!window.ethereum) {
      setError("MetaMask not detected");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      const isNetOk = await checkNetwork(provider);
      if (!isNetOk) {
        setLoading(false);
        return;
      }
      const signer = await provider.getSigner();
      // In a real implementation, you would call your smart contract:
      // const contract = new ethers.Contract(CONTRACT_ADDRESS, ABI, signer);
      // const tx = await contract.registerPresence(presenceData.identifier, presenceData.score, presenceData.firstSeen);
      // await tx.wait();
      alert("Simulated on‑chain anchoring. Replace with actual contract call.");
      const updated = { ...presenceData, anchored: true };
      localStorage.setItem("radiant_presence", JSON.stringify(updated));
      setPresenceData(updated);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Anchoring failed.");
    } finally {
      setLoading(false);
    }
  };

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
            const data = JSON.parse(stored);
            if (data.identifier === accounts[0]) {
              setPresenceData(data);
              setWallet(accounts[0]);
            } else {
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
  }, [wallet]);

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

          {!presenceData ? (
            <Button onClick={connectAndRegister} disabled={loading} className="w-full">
              {loading ? "Connecting..." : "Connect Wallet & Register Presence"}
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
                    {loading ? "Processing..." : "Anchor on‑chain"}
                  </Button>
                )}
                <Button onClick={disconnect} variant="ghost" className="flex-1">
                  Disconnect
                </Button>
              </div>
              {!isCorrectNetwork && (
                <p className="text-xs text-yellow-400">
                  ⚠️ Wrong network. Please switch to {EXPECTED_CHAIN_NAME}.
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
