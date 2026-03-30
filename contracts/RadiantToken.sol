// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract Radiant {
    address public relayer;

    struct User {
        uint256 stake;
        uint256 reputation;
        uint256 rewards;
    }

    mapping(address => User) public users;

    event Staked(address indexed user, uint256 amount);
    event ProofSubmitted(address indexed user, bytes32 proofHash);
    event ProofVerified(address indexed user, uint256 reward);
    event RelayerUpdated(address indexed newRelayer);

    modifier onlyRelayer() {
        require(msg.sender == relayer, "Not relayer");
        _;
    }

    constructor() {
        relayer = msg.sender;
    }

    function setRelayer(address _relayer) external onlyRelayer {
        relayer = _relayer;
        emit RelayerUpdated(_relayer);
    }

    function stake() external payable {
        require(msg.value > 0, "Stake > 0");
        users[msg.sender].stake += msg.value;
        emit Staked(msg.sender, msg.value);
    }

    function submitProof(bytes32 proofHash) external {
        emit ProofSubmitted(msg.sender, proofHash);
    }

    function verifyProof(address user, uint256 reward) external onlyRelayer {
        users[user].reputation += 10;
        users[user].rewards += reward;
        emit ProofVerified(user, reward);
    }

    function claim() external {
        uint256 amount = users[msg.sender].rewards;
        require(amount > 0, "No rewards");
        users[msg.sender].rewards = 0;
        payable(msg.sender).transfer(amount);
    }
}
