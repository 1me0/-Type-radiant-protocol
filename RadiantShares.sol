// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @title RadiantShares
 * @dev Core Economic Engine of the Radiant Protocol. 
 * Implements a 50% Protocol Fee on rewards and Time-Locked Vesting.
 */
contract RadiantShares is ERC20, Ownable {
    
    // --- State Variables ---
    address public protocolFeeRecipient;
    uint256 public constant FEE_DENOMINATOR = 100;
    uint256 public constant FEE_PERCENT = 50;
    uint256 public lockedBalance;

    struct VestingSchedule {
        uint256 totalAmount;
        uint256 start;
        uint256 duration;
        uint256 claimed;
    }

    mapping(address => VestingSchedule) public vesting;
    mapping(address => uint256) public reputation;

    // --- Events ---
    event ProtocolFeeRecipientUpdated(address indexed newRecipient);
    event RewardDistributed(address indexed user, uint256 netReward, uint256 fee);
    event VestingCreated(address indexed user, uint256 amount, uint256 duration);
    event Claimed(address indexed user, uint256 amount);
    event ReputationUpdated(address indexed user, uint256 weight);

    constructor(address _protocolFeeRecipient) ERC20("Radiant Share", "RAD") {
        require(_protocolFeeRecipient != address(0), "Invalid fee recipient");
        protocolFeeRecipient = _protocolFeeRecipient;
        // Mint initial supply to the Radiant Architect (deployer)
        _mint(msg.sender, 1_000_000 * 10**decimals()); 
    }

    // --- Administrative Functions ---

    function setProtocolFeeRecipient(address newRecipient) external onlyOwner {
        require(newRecipient != address(0), "Zero address not allowed");
        protocolFeeRecipient = newRecipient;
        emit ProtocolFeeRecipientUpdated(newRecipient);
    }

    function setReputation(address user, uint256 weight) external onlyOwner {
        reputation[user] = weight;
        emit ReputationUpdated(user, weight);
    }

    // --- Economic Logic: Rewards & Fees ---

    /**
     * @dev Distributes rewards from the Owner's balance. 
     * 50% is automatically redirected to the protocol recipient.
     */
    function reward(address user, uint256 baseAmount) external onlyOwner {
        require(user != address(0), "Invalid user");
        require(baseAmount > 0, "Reward must be positive");
        require(balanceOf(owner()) >= baseAmount, "Insufficient balance in Architect wallet");

        uint256 fee = (baseAmount * FEE_PERCENT) / FEE_DENOMINATOR;
        uint256 netReward = baseAmount - fee;

        if (fee > 0) {
            _transfer(owner(), protocolFeeRecipient, fee);
        }
        if (netReward > 0) {
            _transfer(owner(), user, netReward);
        }

        emit RewardDistributed(user, netReward, fee);
    }

    // --- Temporal Logic: Vesting ---

    /**
     * @dev Locks tokens from the Owner's balance into a vesting schedule for a user.
     */
    function createVesting(address user, uint256 amount, uint256 durationSeconds) external onlyOwner {
        require(amount <= balanceOf(owner()), "Insufficient balance to vest");
        
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

    /**
     * @dev Allows users to claim their vested tokens based on elapsed time.
     */
    function claim() external {
        VestingSchedule storage v = vesting[msg.sender];
        require(v.totalAmount > 0, "No vesting schedule found");

        uint256 elapsed = block.timestamp - v.start;
        uint256 vested;

        if (elapsed >= v.duration) {
            vested = v.totalAmount;
        } else {
            vested = (v.totalAmount * elapsed) / v.duration;
        }

        uint256 claimable = vested - v.claimed;
        require(claimable > 0, "Nothing to claim yet");

        v.claimed += claimable;
        lockedBalance -= claimable;

        _transfer(address(this), msg.sender, claimable);
        emit Claimed(msg.sender, claimable);
    }
}
const REQUIRED_CONTRACT_ADDRESS = process.env.REACT_APP_RADIANT_SHARES;
const EXPECTED_CHAIN_ID = 42161; // Arbitrum

if (chainId !== EXPECTED_CHAIN_ID) {
    alert("Wrong network");
    return;
}
const code = await provider.getCode(REQUIRED_CONTRACT_ADDRESS);
if (code === "0x") {
    alert("Invalid contract address");
    return;
}
