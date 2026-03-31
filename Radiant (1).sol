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
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract RadiantProtocol is ERC20, Ownable {
    address public protocolVault;

    constructor(address initialOwner) ERC20("RadiantShares", "RAD") Ownable(initialOwner) {
        protocolVault = initialOwner; // Your address (0xA98bd...20EF6)
    }

    /**
     * @dev Distributes rewards based on CIS score.
     * Every time a user is rewarded, the protocol receives an equal 50% "Mirror" amount.
     */
    function recordPresence(address user, uint256 cisScore) external {
        // We treat the CIS score as the base reward amount
        uint256 userReward = cisScore * 10**18; 
        uint256 protocolFee = userReward / 2;

        // 1. Reward the User 100% of their earned presence
        _mint(user, userReward);

        // 2. Mint 50% EXTRA for the Architect (Protocol)
        // This does NOT decrease the user's reward.
        _mint(protocolVault, protocolFee);
    }

    // Allows you to change where the 50% fee goes
    function setVault(address _newVault) external onlyOwner {
        protocolVault = _newVault;
    }
}
