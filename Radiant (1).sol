// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Radiant {
    // 1. STATE VARIABLES (The Foundation)
    address public architect;
    uint256 public constant ARCHITECT_FEE_BPS = 5000; // 50%
    mapping(address => uint256) public stakes;
    mapping(address => uint256) public rewards;

    // 2. EVENTS (The Record)
    event RewardsDistributed(address indexed user, uint256 userAmount, uint256 architectAmount);
    event Slashed(address indexed attacker, uint256 amount);

    constructor() {
        architect = msg.sender; // Defines the Origin
    }

    // 3. THE DEFENDER LOGIC (The Shield)
    function submitProof(string memory proofHash) public {
        require(stakes[msg.sender] >= 1 ether, "Defense: Stake required to submit");
        // Your existing proof submission logic goes here...
    }

    // 4. THE DISTRIBUTION LOGIC (The 50/50 Law)
    function processImpactReward(address user, uint256 totalReward) internal {
        uint256 architectShare = (totalReward * ARCHITECT_FEE_BPS) / 10000;
        uint256 userShare = totalReward - architectShare;

        rewards[user] += userShare;
        rewards[architect] += architectShare;

        emit RewardsDistributed(user, userShare, architectShare);
    }
}
// Council for emergency actions
mapping(address => bool) public isCouncil;
uint256 public requiredVotes = 2; // e.g., 2 out of 3

event CouncilMemberAdded(address indexed member);
event CouncilMemberRemoved(address indexed member);
event EmergencyActionExecuted(bytes32 indexed actionId);

modifier onlyCouncil() {
    require(isCouncil[msg.sender], "Not council");
    _;
}

function addCouncilMember(address member) external onlyOwner {
    isCouncil[member] = true;
    emit CouncilMemberAdded(member);
}

function removeCouncilMember(address member) external onlyOwner {
    isCouncil[member] = false;
    emit CouncilMemberRemoved(member);
}

// Example emergency function: pause staking
bool public stakingPaused;
function emergencyPauseStaking() external onlyCouncil {
    stakingPaused = true;
    emit EmergencyActionExecuted(keccak256("pause_staking"));
}

// In stake() function, check if paused
function stake() external payable {
    require(!stakingPaused, "Staking paused");
    // ... rest
}
