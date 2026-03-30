import React, { useState, useEffect } from 'react';
import { ethers } from 'ethers';
import { RadiantSDK } from '../../RadiantSDK';
import { ProofStatus } from '../../types';

const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:4000';
const CONTRACT_ADDRESS = process.env.REACT_APP_CONTRACT_ADDRESS || '0x...';

function App() {
  const [account, setAccount] = useState<string | null>(null);
  const [sdk, setSdk] = useState<RadiantSDK | null>(null);
  const [stats, setStats] = useState<any>(null);
  const [proofs, setProofs] = useState<ProofStatus[]>([]);
  const [stakeAmount, setStakeAmount] = useState('');

  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'proof_validated') {
        setProofs((prev) =>
          prev.map((p) =>
            p.user === data.payload.user && p.status === 'Pending'
              ? { ...p, status: 'Valid', reward: data.payload.reward }
              : p
          )
        );
        if (sdk) sdk.loadUserStats(account!).then(setStats);
      }
    };
    return () => ws.close();
  }, [sdk, account]);

  const connectWallet = async () => {
    if (!window.ethereum) return alert('Install MetaMask');
    const provider = new ethers.BrowserProvider(window.ethereum);
    await provider.send('eth_requestAccounts', []);
    const signer = await provider.getSigner();
    const addr = await signer.getAddress();
    const sdk = new RadiantSDK(CONTRACT_ADDRESS, signer);
    setAccount(addr);
    setSdk(sdk);
    const userStats = await sdk.loadUserStats(addr);
    setStats(userStats);
  };

  const stake = async () => {
    if (!sdk || !stakeAmount) return;
    await sdk.stake(stakeAmount);
    const userStats = await sdk.loadUserStats(account!);
    setStats(userStats);
    setStakeAmount('');
  };

  const submitProof = async () => {
    if (!sdk) return;
    const proofHash = ethers.keccak256(ethers.toUtf8Bytes(Math.random().toString()));
    await sdk.submitProof(proofHash);
    setProofs((prev) => [{ user: account!, status: 'Pending', hash: proofHash.slice(0,10) }, ...prev]);
  };

  const claim = async () => {
    if (!sdk) return;
    await sdk.claim();
    const userStats = await sdk.loadUserStats(account!);
    setStats(userStats);
  };

  const short = (addr: string) => addr.slice(0,6)+'...'+addr.slice(-4);

  return (
    <div style={{ padding: 20 }}>
      <h1>✨ Radiant Protocol</h1>
      <button onClick={connectWallet}>
        {account ? short(account) : 'Connect Wallet'}
      </button>

      {stats && (
        <div style={{ margin: '20px 0' }}>
          <p>Stake: {stats.stake} ETH</p>
          <p>Reputation: {stats.reputation}</p>
          <p>Rewards: {stats.rewards} ETH</p>
        </div>
      )}

      <div>
        <input
          value={stakeAmount}
          onChange={e => setStakeAmount(e.target.value)}
          placeholder="ETH to stake"
        />
        <button onClick={stake}>Stake</button>
      </div>

      <button onClick={submitProof}>Submit Proof</button>
      <button onClick={claim}>Claim Rewards</button>

      <h2>Proof Submissions</h2>
      {proofs.map((p, i) => (
        <div key={i}>
          {short(p.user)} — {p.status} {p.hash && `(hash: ${p.hash})`}
        </div>
      ))}
    </div>
  );
}

export default App;
