// --- ADD THIS TO YOUR FRONTEND SCRIPT ---

async function submitScoreToContract(score, messageText) {
    // 1. Connectivity Check
    if (!window.ethereum) {
        alert("Please install MetaMask to claim rewards.");
        return;
    }

    try {
        const provider = new ethers.BrowserProvider(window.ethereum);
        const signer = await provider.getSigner();
        
        // 2. Prepare the Message (The Logic)
        // Note: Scaling score by 100 to fit the 1000 max in Radiant.sol
        const scaledScore = Math.min(Math.floor(score * 100), 1000);
        const message = `Radiant CIS Score: ${scaledScore} | Content: ${messageText}`;
        
        // 3. Sign and Hash
        const signature = await signer.signMessage(message);
        const messageHash = ethers.hashMessage(message);

        // 4. Execute Contract Call
        const contract = new ethers.Contract(CONTRACT_ADDRESS, RADIANT_ABI, signer);
        
        console.log("Submitting to Radiant Protocol...");
        const tx = await contract.submitCISScore(scaledScore, messageHash, signature);
        
        await tx.wait();
        alert(`Success! Reputation increased by ${scaledScore / 10}.`);
        
    } catch (error) {
        console.error("Submission failed:", error);
        alert("Transaction failed. Check console for details.");
    }
}
