// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title PrivateOptOut
 * @notice Private voting for protocol consent. All votes must be revealed and all must be YES for the protocol to be allowed.
 * 
 * Features:
 * - Commit‑reveal scheme for private voting.
 * - All participants must vote YES for the protocol to be approved.
 * - Deadline can be extended only by the owner.
 * - After deadline and full revelation, the result is final.
 */
contract PrivateOptOut is Ownable {
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

    constructor(uint256 _durationSeconds) Ownable(msg.sender) {
        deadline = block.timestamp + _durationSeconds;
    }

    /**
     * @dev Commit a vote using a hash of (choice, salt).
     * @param commitment keccak256(abi.encodePacked(choice, salt))
     */
    function commitVote(bytes32 commitment) external onlyBeforeDeadline {
        require(!finalized, "Already finalized");
        require(votes[msg.sender].commitment == 0, "Already voted");
        votes[msg.sender].commitment = commitment;
        totalParticipants++;
        emit VoteCommitted(msg.sender);
    }

    /**
     * @dev Reveal a previously committed vote.
     * @param choice true = YES, false = NO
     * @param salt The salt used in the commitment.
     */
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

    /**
     * @dev Finalize the vote after the deadline. All votes must be revealed.
     * The protocol is allowed only if every participant voted YES.
     */
    function finalize() external onlyAfterDeadline {
        require(!finalized, "Already finalized");
        require(revealedCount == totalParticipants, "Not all votes revealed");
        finalized = true;
        uint256 noCount = totalParticipants - yesCount;
        bool allowed = (yesCount == totalParticipants);
        emit ResultPublished(yesCount, noCount, allowed);
    }

    /**
     * @dev Returns whether the protocol is allowed (must be finalized and unanimous YES).
     */
    function protocolAllowed() external view returns (bool) {
        return finalized && yesCount == totalParticipants && totalParticipants > 0;
    }

    /**
     * @dev Extend the voting deadline (only owner).
     * @param additionalSeconds Seconds to add to the deadline.
     */
    function extendDeadline(uint256 additionalSeconds) external onlyOwner {
        require(additionalSeconds > 0, "Must add positive seconds");
        deadline += additionalSeconds;
        emit DeadlineExtended(deadline);
    }
}
