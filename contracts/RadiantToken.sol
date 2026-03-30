// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract RadiantShares is ERC20, Ownable {
    struct VestingSchedule {
        uint256 totalAmount;
        uint256 start;
        uint256 duration;
        uint256 claimed;
    }

    mapping(address => VestingSchedule) public vesting;
    mapping(address => uint256) public reputation;
    uint256 public lockedBalance;

    event Staked(address indexed user, uint256 amount);
    event ReputationUpdated(address indexed user, uint256 weight);
    event VestingCreated(address indexed user, uint256 amount, uint256 duration);
    event RewardDistributed(address indexed user, uint256 amount);
    event Claimed(address indexed user, uint256 amount);

    constructor() ERC20("Radiant Share", "RAD") {
        _mint(msg.sender, 1_000_000 * 10**decimals());
    }

    // Set or update reputation (only owner)
    function setReputation(address user, uint256 weight) external onlyOwner {
        reputation[user] = weight;
        emit ReputationUpdated(user, weight);
    }

    // Create a vesting schedule (owner only)
    function createVesting(address user, uint256 amount, uint256 durationSeconds) external onlyOwner {
        require(amount <= balanceOf(owner()), "Not enough balance to vest");
        _transfer(owner(), address(this), amount);
        lockedBalance += amount;

        vesting[user] = VestingSchedule({
            totalAmount: amount,
            start: block.timestamp,
            duration: durationSeconds,
            claimed: 0
        });

        emit VestingCreated(user, amount, durationSeconds);
    }

    // Claim vested tokens
    function claim() external {
        VestingSchedule storage v = vesting[msg.sender];
        require(v.totalAmount > 0, "No vesting schedule found");

        uint256 elapsed = block.timestamp - v.start;
        uint256 vested = v.totalAmount * elapsed / v.duration;
        uint256 claimable = vested - v.claimed;
        require(claimable > 0, "Nothing to claim");

        v.claimed += claimable;
        lockedBalance -= claimable;
        _transfer(address(this), msg.sender, claimable);
        emit Claimed(msg.sender, claimable);
    }

    // Reward contributor based on reputation (only owner)
    function reward(address user, uint256 baseAmount) external onlyOwner {
        uint256 weight = reputation[user] + 1; // minimum 1x
        uint256 total = baseAmount * weight;
        require(total <= balanceOf(owner()), "Not enough balance");
        _transfer(owner(), user, total);
        emit RewardDistributed(user, total);
    }
}
// Add to Radiant.sol
import "./RadiantShares.sol";

contract Radiant {
    RadiantShares public radiantToken;
    // ... existing code ...

    constructor(address tokenAddress) {
        radiantToken = RadiantShares(tokenAddress);
        // ... rest
    }

    function verifyProof(address user, uint256 reward) external onlyRelayer {
        // mint tokens to user (if token supports minting, otherwise transfer from treasury)
        radiantToken.reward(user, reward); // reward function expects baseAmount; adjust as needed
        users[user].reputation += 10;
        emit ProofVerified(user, reward);
    }
}
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "./RadiantShares.sol";

contract Radiant {
    // 1. STATE (The Foundation - KEEP THIS)
    address public architect;
    RadiantShares public radiantToken;
    uint256 public constant ARCHITECT_FEE_BPS = 5000; // 50% split

    struct User {
        uint256 stake;
        uint256 reputation;
    }
    mapping(address => User) public users;

    // 2. EVENTS (The Record - ADD NEW ONES HERE)
    event RewardsDistributed(address indexed user, uint256 userAmount, uint256 architectAmount);
    event Slashed(address indexed user, uint256 amount);
    event ProofVerified(address indexed user, uint256 reward);

    // 3. CONSTRUCTOR (The Origin - UPDATE TO LINK TOKEN)
    constructor(address tokenAddress) {
        architect = msg.sender;
        radiantToken = RadiantShares(tokenAddress);
    }

    // 4. ACCESS CONTROL (The Guard)
    modifier onlyRelayer() {
        // In production, require(msg.sender == trustedRelayer);
        _;
    }

    // 5. FUNCTIONS (The Executive - ADD NEW LOGIC HERE)
    
    // The Reward Logic
    function verifyProof(address user, uint256 reward) external onlyRelayer {
        radiantToken.reward(user, reward); 
        users[user].reputation += 10;
        
        // Apply the 50/50 Architect split logic here if needed
        emit ProofVerified(user, reward);
    }

    // The Defense Logic (The Slasher)
    function slash(address user, uint256 amount) external onlyRelayer {
        require(users[user].stake >= amount, "Insufficient stake");
        users[user].stake -= amount;
        emit Slashed(user, amount);
    }
}
