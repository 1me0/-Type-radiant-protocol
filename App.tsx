import React, { useState, useEffect } from 'react';
import { ethers } from 'ethers';
import MessageIntelligence from './components/MessageIntelligence';

const RADIANT_ADDRESS = "YOUR_DEPLOYED_CONTRACT_ADDRESS";
const ABI = [ /* Paste the ABI from your artifacts/contracts/Radiant.sol/Radiant.json here */ ];

function App() {
  const [account, setAccount] = useState<string | null>(null);
  const [contract, setContract] = useState<ethers.Contract | null>(null);

  const connectWallet = async () => {
    if (window.ethereum) {
      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();
      const address = await signer.getAddress();
      const radiantContract = new ethers.Contract(RADIANT_ADDRESS, ABI, signer);
      
      setAccount(address);
      setContract(radiantContract);
    } else {
      alert("Please install a Web3 Wallet (OKX/MetaMask)");
    }
  };

  return (
    <div className="App" style={{ background: '#0f172a', color: 'white', minHeight: '100vh' }}>
      <header style={{ padding: '20px', borderBottom: '1px solid #1e293b', textAlign: 'center' }}>
        <h1>Radiant Protocol v1.0</h1>
        {!account ? (
          <button onClick={connectWallet} style={{ padding: '10px 20px', borderRadius: '8px' }}>
            Connect Radiant Identity
          </button>
        ) : (
          <p>Connected: {account.substring(0, 6)}...{account.substring(38)}</p>
        )}
      </header>
      
      <main>
        {account && <MessageIntelligence contract={contract} account={account} />}
      </main>
    </div>
  );
}

export default App;

