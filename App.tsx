import React, { useState, useEffect, useCallback } from 'react';
import { ethers } from 'ethers';
import MessageIntelligence from './components/MessageIntelligence';
import contractABI from './abis/Radiant.json'; // Ensure path is correct

// Environment variables (create .env file)
const RADIANT_ADDRESS = import.meta.env.VITE_RADIANT_ADDRESS as string;
const EXPECTED_CHAIN_ID = parseInt(import.meta.env.VITE_EXPECTED_CHAIN_ID || '11155111'); // Sepolia
const EXPECTED_CHAIN_NAME = import.meta.env.VITE_EXPECTED_CHAIN_NAME || 'Sepolia';

declare global {
  interface Window {
    ethereum?: ethers.Eip1193Provider & { on?: (event: string, listener: (...args: any[]) => void) => void };
  }
}

function App() {
  const [account, setAccount] = useState<string | null>(null);
  const [contract, setContract] = useState<ethers.Contract | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [initializingContract, setInitializingContract] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [networkOk, setNetworkOk] = useState(false);

  // Validate contract address
  const isContractAddressValid = RADIANT_ADDRESS && ethers.isAddress(RADIANT_ADDRESS);

  // Initialize contract instance
  const initContract = useCallback(async () => {
    if (!window.ethereum || !account || !networkOk) return;
    if (!isContractAddressValid) {
      setError('System Error: Protocol Coordinate (Address) Invalid. Please check environment variables.');
      setContract(null);
      return;
    }

    setInitializingContract(true);
    setError(null);
    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();
      const radiantContract = new ethers.Contract(RADIANT_ADDRESS, contractABI, signer);
      setContract(radiantContract);
    } catch (err: any) {
      setError(`Contract initialization failed: ${err.message}`);
      setContract(null);
    } finally {
      setInitializingContract(false);
    }
  }, [account, networkOk, isContractAddressValid]);

  // Check and optionally switch network
  const checkNetwork = async (): Promise<boolean> => {
    if (!window.ethereum) return false;
    const provider = new ethers.BrowserProvider(window.ethereum);
    const network = await provider.getNetwork();
    const chainId = Number(network.chainId);
    if (chainId !== EXPECTED_CHAIN_ID) {
      setNetworkOk(false);
      setError(`Wrong network. Please switch to ${EXPECTED_CHAIN_NAME} (chain ID ${EXPECTED_CHAIN_ID}).`);
      // Attempt automatic switch
      try {
        await window.ethereum.request({
          method: 'wallet_switchEthereumChain',
          params: [{ chainId: ethers.toBeHex(EXPECTED_CHAIN_ID) }],
        });
        // After switch, page will reload due to chainChanged event, so we return false here.
        return false;
      } catch (switchError: any) {
        // User rejected or another error
        setError(`Please switch to ${EXPECTED_CHAIN_NAME} manually. (${switchError.message})`);
        return false;
      }
    }
    setNetworkOk(true);
    setError(null);
    return true;
  };

  // Connect wallet
  const connectWallet = async () => {
    if (!window.ethereum) {
      setError('No Web3 wallet detected. Please install MetaMask or OKX Wallet.');
      return;
    }
    setConnecting(true);
    setError(null);
    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      const accounts = await provider.send('eth_requestAccounts', []);
      const isCorrect = await checkNetwork();
      if (!isCorrect) {
        setConnecting(false);
        return;
      }
      setAccount(accounts[0]);
      await initContract();
    } catch (err: any) {
      setError(err.message || 'Failed to connect wallet');
    } finally {
      setConnecting(false);
    }
  };

  // Disconnect (clear local state, MetaMask remains connected)
  const disconnect = () => {
    setAccount(null);
    setContract(null);
    setError(null);
    setNetworkOk(false);
  };

  // Retry network switch manually
  const retryNetworkSwitch = async () => {
    setError(null);
    const success = await checkNetwork();
    if (success && account) {
      await initContract();
    }
  };

  // Event listeners
  useEffect(() => {
    if (!window.ethereum) return;
    const handleAccountsChanged = (accounts: string[]) => {
      if (accounts.length === 0) {
        disconnect();
      } else {
        setAccount(accounts[0]);
        initContract();
      }
    };
    const handleChainChanged = () => {
      window.location.reload();
    };

    window.ethereum.on?.('accountsChanged', handleAccountsChanged);
    window.ethereum.on?.('chainChanged', handleChainChanged);
    return () => {
      window.ethereum?.removeListener?.('accountsChanged', handleAccountsChanged);
      window.ethereum?.removeListener?.('chainChanged', handleChainChanged);
    };
  }, [initContract]);

  // Re-initialize contract when account or network changes
  useEffect(() => {
    if (account && networkOk) {
      initContract();
    }
  }, [account, networkOk, initContract]);

  // Re-check network when account changes
  useEffect(() => {
    if (account) {
      checkNetwork();
    }
  }, [account]);

  return (
    <div style={{ background: '#0f172a', color: 'white', minHeight: '100vh', fontFamily: 'system-ui' }}>
      <header style={{ padding: '20px', borderBottom: '1px solid #1e293b', textAlign: 'center' }}>
        <h1 style={{ margin: 0 }}>Radiant Protocol v1.0</h1>
        <p style={{ marginTop: '8px', color: '#94a3b8' }}>Proof‑of‑Presence · ZK‑Recursive Identity</p>
        <div style={{ marginTop: '16px' }}>
          {!account ? (
            <button
              onClick={connectWallet}
              disabled={connecting}
              style={{
                padding: '10px 20px',
                borderRadius: '40px',
                border: 'none',
                background: connecting ? '#475569' : '#3b82f6',
                color: 'white',
                fontWeight: 'bold',
                cursor: connecting ? 'not-allowed' : 'pointer',
                transition: 'background 0.2s',
              }}
            >
              {connecting ? 'Connecting...' : 'Connect Radiant Identity'}
            </button>
          ) : (
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center', justifyContent: 'center', flexWrap: 'wrap' }}>
              <span style={{ background: '#1e293b', padding: '6px 12px', borderRadius: '40px', fontSize: '0.9rem' }}>
                🔗 {account.slice(0, 6)}...{account.slice(-4)}
              </span>
              {!networkOk && (
                <span style={{ background: '#dc2626', padding: '4px 10px', borderRadius: '40px', fontSize: '0.8rem' }}>
                  ⚠️ Wrong network
                </span>
              )}
              <button
                onClick={disconnect}
                style={{
                  padding: '6px 14px',
                  borderRadius: '40px',
                  border: '1px solid #64748b',
                  background: 'transparent',
                  color: '#cbd5e1',
                  cursor: 'pointer',
                }}
              >
                Disconnect
              </button>
            </div>
          )}
        </div>
        {error && (
          <div style={{ marginTop: '12px', background: '#7f1a1a', padding: '8px 16px', borderRadius: '40px', display: 'inline-block' }}>
            ❌ {error}
            {error.includes('Please switch') && (
              <button
                onClick={retryNetworkSwitch}
                style={{
                  marginLeft: '12px',
                  background: '#3b82f6',
                  border: 'none',
                  borderRadius: '20px',
                  padding: '4px 12px',
                  color: 'white',
                  cursor: 'pointer',
                }}
              >
                Retry Switch
              </button>
            )}
          </div>
        )}
      </header>
      <main style={{ padding: '24px' }}>
        {account && networkOk && !initializingContract && contract && (
          <MessageIntelligence contract={contract} account={account} />
        )}
        {account && networkOk && initializingContract && (
          <div style={{ textAlign: 'center', padding: '40px', background: '#1e293b', borderRadius: '24px' }}>
            <p>⏳ Initializing contract...</p>
          </div>
        )}
        {account && !networkOk && (
          <div style={{ textAlign: 'center', padding: '40px', background: '#1e293b', borderRadius: '24px' }}>
            <p>⚠️ Please switch to {EXPECTED_CHAIN_NAME} network to use the Radiant Protocol.</p>
            <button
              onClick={retryNetworkSwitch}
              style={{ marginTop: '12px', padding: '8px 20px', borderRadius: '40px', background: '#3b82f6', border: 'none', color: 'white', cursor: 'pointer' }}
            >
              Switch to {EXPECTED_CHAIN_NAME}
            </button>
          </div>
        )}
        {!account && (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: '#94a3b8' }}>
            <p>✨ Connect your wallet to start your Radiant presence.</p>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
