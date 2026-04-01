// --- ADD TO RADIANT.SOL ---

mapping(address => bool) public isCouncil;
uint256 public councilCount;
uint256 public requiredVotes;

struct EmergencyAction {
    bool active;
    uint256 voteCount;
    mapping(address => bool) hasVoted;
}

// Separate vectors for granular control
bool public stakingPaused;
bool public proofsPaused;
bool public rewardsFrozen;

mapping(bytes32 => EmergencyAction) public pendingActions;

event EmergencyTriggered(string action, bool status);

modifier onlyCouncil() {
    require(isCouncil[msg.sender], "Caller is not a Council member");
    _;
}

/**
 * @dev Triggers a vote for an emergency action. 
 * Once votes >= requiredVotes, the action is executed.
 */
function voteEmergencyAction(string memory actionName, bool pause) external onlyCouncil {
    bytes32 actionId = keccak256(abi.encodePacked(actionName, pause));
    EmergencyAction storage action = pendingActions[actionId];

    require(!action.hasVoted[msg.sender], "Already voted");
    
    action.hasVoted[msg.sender] = true;
    action.voteCount++;

    if (action.voteCount >= requiredVotes) {
        executeEmergencyAction(actionName, pause);
        delete pendingActions[actionId]; // Reset for future use
    }
}

function executeEmergencyAction(string memory name, bool status) internal {
    if (compareStrings(name, "staking")) stakingPaused = status;
    if (compareStrings(name, "proofs")) proofsPaused = status;
    if (compareStrings(name, "rewards")) rewardsFrozen = status;
    
    emit EmergencyTriggered(name, status);
}

// Helper to compare strings in Solidity
function compareStrings(string memory a, string memory b) internal pure returns (bool) {
    return (keccak256(abi.encodePacked(a)) == keccak256(abi.encodePacked(b)));
}
