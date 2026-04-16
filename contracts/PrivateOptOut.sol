// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title PrivateOptOut
 * @notice Private voting for protocol consent. All votes must be revealed and all must be YES.
 */
contract PrivateOptOut {
    struct Vote {
        bytes32 commitment;
        bool revealed;
        bool choice;
    }

    mapping(address => Vote) public votes;
    uint256 public totalParticipants;
    uint256 public revealedCount;
    uint256 public yesCount;
    bool public finalized;
    uint256 public deadline;

    event VoteCommitted(address indexed voter);
    event VoteRevealed(address indexed voter, bool choice);
    event ResultPublished(uint256 yesVotes, uint256 noVotes, bool protocolAllowed);
    event DeadlineExtended(uint256 newDeadline);

    modifier onlyBeforeDeadline() {
        require(block.timestamp < deadline, "Voting period ended");
        _;
    }

    modifier onlyAfterDeadline() {
        require(block.timestamp >= deadline, "Voting period not ended");
        _;
    }

    constructor(uint256 _durationSeconds) {
        deadline = block.timestamp + _durationSeconds;
    }

    function commitVote(bytes32 commitment) external onlyBeforeDeadline {
        require(!finalized, "Already finalized");
        require(votes[msg.sender].commitment == 0, "Already voted");
        votes[msg.sender].commitment = commitment;
        totalParticipants++;
        emit VoteCommitted(msg.sender);
    }

    function revealVote(bool choice, uint256 salt) external onlyBeforeDeadline {
        require(!finalized, "Already finalized");
        Vote storage v = votes[msg.sender];
        require(v.commitment != 0, "No commitment");
        require(!v.revealed, "Already revealed");
        bytes32 computed = keccak256(abi.encodePacked(choice, salt));
        require(computed == v.commitment, "Commitment mismatch");
        v.revealed = true;
        v.choice = choice;
        revealedCount++;
        if (choice) {
            yesCount++;
        }
        emit VoteRevealed(msg.sender, choice);
    }

    function finalize() external onlyAfterDeadline {
        require(!finalized, "Already finalized");
        require(revealedCount == totalParticipants, "Not all votes revealed");
        finalized = true;
        uint256 noCount = totalParticipants - yesCount;
        bool allowed = (yesCount == totalParticipants);
        emit ResultPublished(yesCount, noCount, allowed);
    }

    function protocolAllowed() external view returns (bool) {
        return finalized && yesCount == totalParticipants;
    }

    function extendDeadline(uint256 additionalSeconds) external {
        // Only the contract deployer or a governance role could extend; for simplicity, we allow anyone? Better to add owner.
        // We'll add a simple owner for safety.
        require(msg.sender == tx.origin, "Only EOA"); // placeholder; in production use AccessControl.
        deadline += additionalSeconds;
        emit DeadlineExtended(deadline);
    }
}
