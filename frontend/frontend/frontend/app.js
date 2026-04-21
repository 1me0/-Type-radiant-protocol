// frontend/frontend/frontend/app.js
// Radiant Protocol – Frontend Presence Module
// Handles wallet connection, presence pulse, and network validation.

let userAddress = null;
let presenceInterval = null;
let currentPresence = 0;

// Expected network configuration (adjust for your deployment)
const EXPECTED_CHAIN_ID = 11155111; // Sepolia testnet
const EXPECTED_CHAIN_NAME = "Sepolia";

// DOM elements (assumed to exist in the HTML)
const connectBtn = document.getElementById('connect-wallet');
const scoreElement = document.getElementById('presence-score');
const networkStatusSpan = document.getElementById('network-status'); // optional

// Helper: update presence display
function updatePresenceDisplay(value) {
    if (scoreElement) {
        scoreElement.innerText = value.toFixed(4);
    }
}

// Helper: check network and display warning if needed
async function checkNetwork() {
    if (!window.ethereum) return false;
    const provider = new ethers.BrowserProvider(window.ethereum);
    const network = await provider.getNetwork();
    const chainId = Number(network.chainId);
    if (chainId !== EXPECTED_CHAIN_ID) {
        if (networkStatusSpan) {
            networkStatusSpan.innerText = `⚠️ Please switch to ${EXPECTED_CHAIN_NAME}`;
            networkStatusSpan.style.color = "orange";
        }
        return false;
    } else {
        if (networkStatusSpan) {
            networkStatusSpan.innerText = `✅ Connected to ${EXPECTED_CHAIN_NAME}`;
            networkStatusSpan.style.color = "lightgreen";
        }
        return true;
    }
}

// Start the presence pulse (incrementing presence score every second)
function startPresencePulse() {
    if (presenceInterval) clearInterval(presenceInterval);
    presenceInterval = setInterval(() => {
        // Increment presence by a small radiant unit (simulates continuous presence)
        // In a real implementation, this could be derived from block confirmations or proof generation.
        currentPresence += 0.0001;
        updatePresenceDisplay(currentPresence);
    }, 1000);
}

// Stop presence pulse (e.g., on disconnect)
function stopPresencePulse() {
    if (presenceInterval) {
        clearInterval(presenceInterval);
        presenceInterval = null;
    }
}

// Connect wallet and register presence
async function connectIdentity() {
    if (!window.ethereum) {
        alert("Please use a Radiant-compatible browser (MetaMask/Trust).");
        return;
    }
    try {
        // Request accounts
        const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
        userAddress = accounts[0];
        // Update button text
        if (connectBtn) {
            connectBtn.innerText = `ID: ${userAddress.slice(0, 6)}...`;
            connectBtn.disabled = true;
        }
        console.log("Identity Linked:", userAddress);
        
        // Check network after connection
        const isCorrectNetwork = await checkNetwork();
        if (!isCorrectNetwork) {
            // Optionally, prompt user to switch network
            try {
                await window.ethereum.request({
                    method: 'wallet_switchEthereumChain',
                    params: [{ chainId: ethers.toBeHex(EXPECTED_CHAIN_ID) }],
                });
            } catch (switchError) {
                console.error("Network switch failed", switchError);
                alert(`Please switch to ${EXPECTED_CHAIN_NAME} manually.`);
            }
        }
        
        // Start presence measurement
        startPresencePulse();
    } catch (error) {
        console.error("Link Failed", error);
        alert("Connection failed. See console for details.");
    }
}

// Disconnect (clear local state, but MetaMask remains connected)
function disconnect() {
    userAddress = null;
    stopPresencePulse();
    currentPresence = 0;
    updatePresenceDisplay(0);
    if (connectBtn) {
        connectBtn.innerText = "Connect Wallet";
        connectBtn.disabled = false;
    }
    if (networkStatusSpan) {
        networkStatusSpan.innerText = "Not connected";
    }
}

// Listen for account and network changes
if (window.ethereum) {
    window.ethereum.on('accountsChanged', (accounts) => {
        if (accounts.length === 0) {
            disconnect();
        } else if (accounts[0] !== userAddress) {
            // Reload or reconnect with new account
            disconnect();
            connectIdentity();
        }
    });
    window.ethereum.on('chainChanged', () => {
        // Reload the page on network change to reset state
        window.location.reload();
    });
}

// Attach event listener to connect button
if (connectBtn) {
    connectBtn.addEventListener('click', connectIdentity);
}

// Initial check for existing connection (e.g., if page reloads while wallet is already connected)
(async () => {
    if (window.ethereum) {
        try {
            const accounts = await window.ethereum.request({ method: 'eth_accounts' });
            if (accounts.length > 0) {
                userAddress = accounts[0];
                if (connectBtn) connectBtn.innerText = `ID: ${userAddress.slice(0, 6)}...`;
                await checkNetwork();
                startPresencePulse();
            }
        } catch (e) {
            console.warn("Could not auto-connect", e);
        }
    }
})();
