let userAddress = null;

// The Bridge Connection
async function connectIdentity() {
    if (window.ethereum) {
        try {
            const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
            userAddress = accounts[0];
            document.getElementById('connect-wallet').innerText = `ID: ${userAddress.slice(0, 6)}...`;
            console.log("Identity Linked:", userAddress);
            startPresencePulse();
        } catch (error) {
            console.error("Link Failed", error);
        }
    } else {
        alert("Please use a Radiant-compatible browser (MetaMask/Trust).");
    }
}

// The Master Formula in Action: Measuring Presence
function startPresencePulse() {
    setInterval(() => {
        const scoreElement = document.getElementById('presence-score');
        let currentScore = parseFloat(scoreElement.innerText);
        // Incrementing presence score by a small, radiant unit
        scoreElement.innerText = (currentScore + 0.0001).toFixed(4);
    }, 1000);
}

document.getElementById('connect-wallet').addEventListener('click', connectIdentity);

