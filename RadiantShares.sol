// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @title RadiantShares with Protocol Fee
 * @dev Extends the RadiantShares token to take 50% of every reward as protocol fee.
 *      The fee is sent to a designated recipient address.
 */
contract RadiantSharesWithFee is ERC20, Ownable {
    // Fee configuration
    address public protocolFeeRecipient;
    uint256 public constant FEE_DENOMINATOR = 100; // 100% base
    uint256 public constant FEE_PERCENT = 50;      // 50% fee

    // Vesting data
    struct VestingSchedule {
        uint256 totalAmount;
        uint256 start;
        uint256 duration;
        uint256 claimed;
    }

    mapping(address => VestingSchedule) public vesting;
    mapping(address => uint256) public reputation;
    uint256 public lockedBalance;

    // Events
    event ProtocolFeeRecipientUpdated(address indexed newRecipient);
    event ProtocolFeeTaken(address indexed from, address indexed to, uint256 feeAmount, uint256 netReward);
    event Staked(address indexed user, uint256 amount);      // not used in this contract, but could be
    event ReputationUpdated(address indexed user, uint256 weight);
    event VestingCreated(address indexed user, uint256 amount, uint256 duration);
    event RewardDistributed(address indexed user, uint256 netReward, uint256 fee);
    event Claimed(address indexed user, uint256 amount);

    constructor(address _protocolFeeRecipient) ERC20("Radiant Share", "RAD") {
        require(_protocolFeeRecipient != address(0), "Invalid fee recipient");
        protocolFeeRecipient = _protocolFeeRecipient;
        _mint(msg.sender, 1_000_000 * 10**decimals()); // initial mint to deployer
    }

    // ----- Fee management -----
    function setProtocolFeeRecipient(address newRecipient) external onlyOwner {
        require(newRecipient != address(0), "Zero address not allowed");
        protocolFeeRecipient = newRecipient;
        emit ProtocolFeeRecipientUpdated(newRecipient);
    }

    // ----- Reputation (only owner) -----
    function setReputation(address user, uint256 weight) external onlyOwner {
        reputation[user] = weight;
        emit ReputationUpdated(user, weight);
    }

    // ----- Vesting (only owner) -----
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

    // ----- Claim vested tokens -----
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

    // ----- Reward distribution with 50% protocol fee -----
    /**
     * @dev Distributes a reward to a user, taking 50% as protocol fee.
     * @param user The recipient of the net reward.
     * @param baseAmount The total reward amount before fee.
     */
    function reward(address user, uint256 baseAmount) external onlyOwner {
        require(user != address(0), "Invalid user");
        require(baseAmount > 0, "Reward must be positive");

        // Calculate fee and net reward
        uint256 fee = (baseAmount * FEE_PERCENT) / FEE_DENOMINATOR;
        uint256 netReward = baseAmount - fee;

        // Ensure sufficient balance (owner must have enough tokens)
        require(balanceOf(owner()) >= baseAmount, "Insufficient balance for reward");

        // Transfer fee to protocol fee recipient
        if (fee > 0) {
            _transfer(owner(), protocolFeeRecipient, fee);
        }
        // Transfer net reward to user
        if (netReward > 0) {
            _transfer(owner(), user, netReward);
        }

        emit RewardDistributed(user, netReward, fee);
    }

    // Optional: override transfer functions to also apply fee on every transaction?
    // Not done here to keep gas low; only rewards are taxed.
}
