// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Radiant {
    address public architect;
    uint256 public constant ARCHITECT_FEE_BPS = 5000; // 50.00% (Basis Points)

    event RewardsDistributed(address indexed user, uint256 userAmount, uint256 architectAmount);

    constructor() {
        architect = msg.sender; // The one who ignites the protocol
    }

    // Function to process validated impact (Δ)
    function processImpactReward(address user, uint256 totalReward) internal {
        // Calculate the Architect's 50% share
        uint256 architectShare = (totalReward * ARCHITECT_FEE_BPS) / 10000;
        uint256 userShare = totalReward - architectShare;

        // Distribute or Record the value
        rewards[user] += userShare;
        rewards[architect] += architectShare;

        emit RewardsDistributed(user, userShare, architectShare);
    }
}
