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
