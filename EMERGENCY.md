// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title Emergency Council – Pausable Vectors with Multi‑sig Voting
 * @notice Adds council-based emergency controls for staking, proofs, and rewards.
 *         Council members vote on actions; once required votes are reached, the action executes.
 */
contract EmergencyCouncil {
    // --- Council Members ---
    mapping(address => bool) public isCouncil;
    uint256 public councilCount;
    uint256 public requiredVotes;          // number of votes needed to pass an action

    // --- Emergency Control Vectors ---
    bool public stakingPaused;
    bool public proofsPaused;
    bool public rewardsFrozen;

    // --- Voting State ---
    mapping(bytes32 => mapping(address => bool)) public hasVoted;  // actionId => council member => voted
    mapping(bytes32 => uint256) public voteCount;                  // actionId => current votes
    mapping(bytes32 => bool) public actionExecuted;                // prevent re-execution

    // --- Events ---
    event CouncilMemberAdded(address indexed member);
    event CouncilMemberRemoved(address indexed member);
    event RequiredVotesUpdated(uint256 oldVotes, uint256 newVotes);
    event VoteCast(address indexed voter, string actionName, bool pause, uint256 votes);
    event EmergencyActionExecuted(string actionName, bool status);
    event EmergencyVectorUpdated(string vector, bool paused);

    modifier onlyCouncil() {
        require(isCouncil[msg.sender], "EmergencyCouncil: not a council member");
        _;
    }

    constructor(address[] memory initialCouncil, uint256 _requiredVotes) {
        require(initialCouncil.length > 0, "EmergencyCouncil: at least one member");
        require(_requiredVotes > 0 && _requiredVotes <= initialCouncil.length, "EmergencyCouncil: invalid required votes");
        for (uint256 i = 0; i < initialCouncil.length; i++) {
            address member = initialCouncil[i];
            require(member != address(0), "EmergencyCouncil: zero address");
            require(!isCouncil[member], "EmergencyCouncil: duplicate member");
            isCouncil[member] = true;
        }
        councilCount = initialCouncil.length;
        requiredVotes = _requiredVotes;
    }

    /**
     * @dev Add a new council member (only existing council members can propose? 
     *      For simplicity, this function is left for the deployer/admin to manage.
     *      In a full implementation, you would add a vote‑based add/remove mechanism.
     *      Here we keep it simple: only the contract owner or a separate admin role can add.
     *      For demonstration, we skip the admin role and assume the constructor sets the council.
     */
    function addCouncilMember(address newMember) external onlyCouncil {
        require(newMember != address(0), "EmergencyCouncil: zero address");
        require(!isCouncil[newMember], "EmergencyCouncil: already a member");
        isCouncil[newMember] = true;
        councilCount++;
        emit CouncilMemberAdded(newMember);
    }

    function removeCouncilMember(address member) external onlyCouncil {
        require(isCouncil[member], "EmergencyCouncil: not a member");
        isCouncil[member] = false;
        councilCount--;
        emit CouncilMemberRemoved(member);
    }

    function setRequiredVotes(uint256 newVotes) external onlyCouncil {
        require(newVotes > 0 && newVotes <= councilCount, "EmergencyCouncil: invalid votes");
        uint256 old = requiredVotes;
        requiredVotes = newVotes;
        emit RequiredVotesUpdated(old, newVotes);
    }

    /**
     * @dev Cast a vote for an emergency action (pause or unpause a vector).
     * @param actionName One of "staking", "proofs", "rewards"
     * @param pause      true = pause the vector, false = unpause (if already paused)
     */
    function voteEmergencyAction(string calldata actionName, bool pause) external onlyCouncil {
        bytes32 actionId = keccak256(abi.encodePacked(actionName, pause));
        require(!actionExecuted[actionId], "EmergencyCouncil: action already executed");
        require(!hasVoted[actionId][msg.sender], "EmergencyCouncil: already voted");

        hasVoted[actionId][msg.sender] = true;
        voteCount[actionId]++;

        emit VoteCast(msg.sender, actionName, pause, voteCount[actionId]);

        if (voteCount[actionId] >= requiredVotes) {
            _executeEmergencyAction(actionName, pause);
            actionExecuted[actionId] = true;
        }
    }

    function _executeEmergencyAction(string memory actionName, bool pause) internal {
        bytes32 id = keccak256(bytes(actionName));
        if (id == keccak256("staking")) {
            stakingPaused = pause;
            emit EmergencyVectorUpdated("staking", pause);
        } else if (id == keccak256("proofs")) {
            proofsPaused = pause;
            emit EmergencyVectorUpdated("proofs", pause);
        } else if (id == keccak256("rewards")) {
            rewardsFrozen = pause;
            emit EmergencyVectorUpdated("rewards", pause);
        } else {
            revert("EmergencyCouncil: unknown action");
        }
        emit EmergencyActionExecuted(actionName, pause);
    }

    /**
     * @dev Convenience function to get the current state of all vectors.
     */
    function getEmergencyState() external view returns (bool stakingPaused_, bool proofsPaused_, bool rewardsFrozen_) {
        return (stakingPaused, proofsPaused, rewardsFrozen);
    }
}
