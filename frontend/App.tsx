// frontend/App.tsx
// Radiant Protocol – Main Application Component
// Handles wallet connection, staking, proof submission, rewards, and leaderboard gating.

import React, { useState, useEffect, useCallback } from 'react';
import { ethers } from 'ethers';
import { RadiantSDK } from './RadiantSDK';
import { ProofStatus } from './types';

// Environment variables (set in .env)
const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:4000';
const CONTRACT_ADDRESS = process.env.REACT_APP_CONTRACT_ADDRESS || '0x...';

interface UserStats {
  stake: string;
  reputation: number;
  rewards: string;
}

// Mock Leaderboard component (replace with actual implementation)
const Leaderboard: React.FC<{ user: string }> = ({ user }) => (
  <div className="leaderboard">
    <h3>🏆 Sovereign Leaderboard</h3>
    <p>You are among the Radiant: {user.slice(0, 6)}...</p>
    {/* Actual leaderboard logic here */}
  </div>
);

const App: React.FC = () => {
  const [account, setAccount] = useState<string | null>(null);
  const [sdk, setSdk] = useState<RadiantSDK | null>(null);
  const [stats, setStats] = useState<UserStats | null>(null);
  const [proofs, setProofs] = useState<ProofStatus[]>([]);
  const [stakeAmount, setStakeAmount] = useState<string>('');
  const [userScore, setUserScore] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Helper to shorten addresses
  const short = (addr: string) => `${addr.slice(0, 6)}...${addr.slice(-4)}`;

  // WebSocket connection for real‑time proof validation updates
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout;

    const connectWebSocket = () => {
      ws = new WebSocket(WS_URL);
      ws.onopen = () => console.log('WebSocket connected');
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'proof_validated') {
            setProofs((prev) =>
              prev.map((p) =>
                p.user === data.payload.user && p.status === 'Pending'
                  ? { ...p, status: 'Valid', reward: data.payload.reward, hash: p.hash }
                  : p
              )
            );
            if (sdk && account) {
              sdk.loadUserStats(account).then(setStats).catch(console.error);
            }
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message', err);
        }
      };
      ws.onclose = () => {
        console.log('WebSocket disconnected, reconnecting in 3s...');
        reconnectTimeout = setTimeout(connectWebSocket, 3000);
      };
      ws.onerror = (err) => console.error('WebSocket error', err);
    };

    connectWebSocket();

    return () => {
      if (ws) ws.close();
      clearTimeout(reconnectTimeout);
    };
  }, [sdk, account]);

  // Connect wallet and initialise SDK
  const connectWallet = useCallback(async () => {
    if (!window.ethereum) {
      setError('MetaMask not detected. Please install MetaMask.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      await provider.send('eth_requestAccounts', []);
      const signer = await provider.getSigner();
      const addr = await signer.getAddress();
      const radiantSdk = new RadiantSDK(CONTRACT_ADDRESS, signer);
      setAccount(addr);
      setSdk(radiantSdk);
      const userStats = await radiantSdk.loadUserStats(addr);
      setStats(userStats);
      // Simulate userScore from reputation or stake (customise as needed)
      setUserScore(userStats.reputation);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to connect wallet');
    } finally {
      setLoading(false);
    }
  }, []);

  // Stake tokens
  const stake = useCallback(async () => {
    if (!sdk || !stakeAmount) return;
    setLoading(true);
    setError(null);
    try {
      await sdk.stake(stakeAmount);
      const userStats = await sdk.loadUserStats(account!);
      setStats(userStats);
      setUserScore(userStats.reputation);
      setStakeAmount('');
    } catch (err: any) {
      setError(err.message || 'Staking failed');
    } finally {
      setLoading(false);
    }
  }, [sdk, stakeAmount, account]);

  // Submit a random proof (for demo)
  const submitProof = useCallback(async () => {
    if (!sdk) return;
    setLoading(true);
    setError(null);
    try {
      const randomHash = ethers.keccak256(ethers.toUtf8Bytes(Math.random().toString()));
      await sdk.submitProof(randomHash);
      const newProof: ProofStatus = {
        user: account!,
        status: 'Pending',
        hash: randomHash.slice(0, 10),
      };
      setProofs((prev) => [newProof, ...prev]);
    } catch (err: any) {
      setError(err.message || 'Proof submission failed');
    } finally {
      setLoading(false);
    }
  }, [sdk, account]);

  // Claim rewards
  const claim = useCallback(async () => {
    if (!sdk) return;
    setLoading(true);
    setError(null);
    try {
      await sdk.claim();
      const userStats = await sdk.loadUserStats(account!);
      setStats(userStats);
    } catch (err: any) {
      setError(err.message || 'Claim failed');
    } finally {
      setLoading(false);
    }
  }, [sdk, account]);

  // Determine if leaderboard is accessible (requires score >= 100)
  const leaderboardUnlocked = userScore >= 100;

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h1>✨ Radiant Protocol</h1>
      <button onClick={connectWallet} disabled={loading}>
        {account ? short(account) : 'Connect Wallet'}
      </button>
      {error && <p style={{ color: 'red' }}>{error}</p>}

      {stats && (
        <div style={{ margin: '20px 0', padding: '12px', border: '1px solid #ccc', borderRadius: '8px' }}>
          <p><strong>Stake:</strong> {stats.stake} ETH</p>
          <p><strong>Reputation (Presence):</strong> {stats.reputation}</p>
          <p><strong>Rewards:</strong> {stats.rewards} ETH</p>
        </div>
      )}

      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <input
          type="number"
          step="0.01"
          value={stakeAmount}
          onChange={(e) => setStakeAmount(e.target.value)}
          placeholder="ETH to stake"
          style={{ padding: '8px' }}
        />
        <button onClick={stake} disabled={loading}>Stake</button>
        <button onClick={submitProof} disabled={loading}>Submit Proof</button>
        <button onClick={claim} disabled={loading}>Claim Rewards</button>
      </div>

      <div className="radiant-dashboard">
        {leaderboardUnlocked ? (
          <Leaderboard user={account || ''} />
        ) : (
          <div className="gate-overlay" style={{ padding: '20px', border: '1px dashed #ffaa00', borderRadius: '8px', textAlign: 'center' }}>
            <h3>🔒 Leaderboard Locked</h3>
            <p>Current Radiance: {userScore} / 100</p>
            <p>Refine your Presence to see your rank among the Sovereigns.</p>
          </div>
        )}
      </div>

      <h2>Proof Submissions</h2>
      {proofs.length === 0 && <p>No proofs submitted yet.</p>}
      {proofs.map((p, i) => (
        <div key={i} style={{ marginBottom: '4px', fontFamily: 'monospace' }}>
          {short(p.user)} — {p.status} {p.hash && `(hash: ${p.hash})`}
          {p.reward && ` — reward: ${p.reward}`}
        </div>
      ))}
    </div>
  );
};

export default App;
