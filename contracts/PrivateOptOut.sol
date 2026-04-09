// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract PrivateOptOut {
    struct Vote {
        bytes32 commitment;
        bool revealed;
    }

    mapping(address => Vote) public votes;
    uint256 public totalParticipants;
    uint256 public yesCount;
    bool public finalized;

    event VoteCommitted(address indexed voter);
    event VoteRevealed(address indexed voter, bool choice);
    event ResultPublished(uint256 yesVotes, uint256 noVotes);

    function commitVote(bytes32 commitment) external {
        require(!finalized, "Already finalized");
        require(votes[msg.sender].commitment == 0, "Already voted");
        votes[msg.sender].commitment = commitment;
        totalParticipants++;
        emit VoteCommitted(msg.sender);
    }

    function revealVote(bool choice, uint256 salt) external {
        require(!finalized, "Already finalized");
        Vote storage v = votes[msg.sender];
        require(v.commitment != 0 && !v.revealed, "Invalid");
        bytes32 computed = keccak256(abi.encodePacked(choice, salt));
        require(computed == v.commitment, "Commitment mismatch");
        v.revealed = true;
        if (choice) yesCount++;
        emit VoteRevealed(msg.sender, choice);
    }

    function finalize() external {
        require(!finalized, "Already finalized");
        finalized = true;
        uint256 noCount = totalParticipants - yesCount;
        emit ResultPublished(yesCount, noCount);
    }

    function protocolAllowed() external view returns (bool) {
        return finalized && yesCount == totalParticipants;
    }
}
