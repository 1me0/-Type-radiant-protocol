// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";

/**
 * @title ArchitectFeeV2
 * @notice Competitive fee game contract:
 *         - Configurable fee on token transfers (default 50%, max 50%).
 *         - If transfer amount > last recorded amount, sender receives a bonus equal to the fee (paid from treasury).
 *         - Governance roles with timelock on sensitive parameters (fee, architect address).
 *         - Treasury can be funded by fee managers.
 *         - Architect can withdraw treasury funds.
 *         - Pausable for emergencies.
 */
contract ArchitectFeeV2 is AccessControl, ReentrancyGuard, Pausable {
    bytes32 public constant GOVERNOR_ROLE = keccak256("GOVERNOR_ROLE");
    bytes32 public constant ARCHITECT_ROLE = keccak256("ARCHITECT_ROLE");
    bytes32 public constant FEE_MANAGER_ROLE = keccak256("FEE_MANAGER_ROLE");

    IERC20 public token;
    address public architect;
    uint256 public lastRecordAmount;
    uint256 public feeBasisPoints;        // e.g., 5000 = 50%
    uint256 public constant MAX_FEE_BASIS_POINTS = 5000; // 50% max

    // Timelock for fee change
    struct PendingFee {
        uint256 value;
        uint256 timestamp;
    }
    PendingFee public pendingFee;

    // Timelock for architect address change
    struct PendingArchitect {
        address value;
        uint256 timestamp;
    }
    PendingArchitect public pendingArchitect;

    uint256 public constant TIMELOCK_DELAY = 2 days;

    // Treasury balance (tokens held by this contract for bonuses)
    uint256 public treasuryBalance;

    // Events
    event TransferWithFee(
        address indexed from,
        address indexed to,
        uint256 amount,
        uint256 fee,
        bool bonusPaid,
        uint256 bonusAmount
    );
    event RecordUpdated(uint256 newRecord);
    event FeeProposed(uint256 newFee, uint256 timestamp);
    event FeeExecuted(uint256 newFee);
    event ArchitectProposed(address indexed newArchitect, uint256 timestamp);
    event ArchitectExecuted(address indexed newArchitect);
    event TreasuryFunded(address indexed funder, uint256 amount);
    event TreasuryWithdrawn(address indexed to, uint256 amount);
    event Paused(address indexed account);
    event Unpaused(address indexed account);

    modifier onlyGovernor() {
        require(hasRole(GOVERNOR_ROLE, msg.sender), "Not governor");
        _;
    }

    modifier onlyArchitect() {
        require(hasRole(ARCHITECT_ROLE, msg.sender), "Not architect");
        _;
    }

    modifier onlyFeeManager() {
        require(hasRole(FEE_MANAGER_ROLE, msg.sender), "Not fee manager");
        _;
    }

    constructor(address _token, address _architect, uint256 _feeBasisPoints) {
        require(_token != address(0), "Invalid token");
        require(_architect != address(0), "Invalid architect");
        require(_feeBasisPoints <= MAX_FEE_BASIS_POINTS, "Fee too high");

        token = IERC20(_token);
        architect = _architect;
        feeBasisPoints = _feeBasisPoints;
        lastRecordAmount = 0;
        treasuryBalance = 0;

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(GOVERNOR_ROLE, msg.sender);
        _grantRole(ARCHITECT_ROLE, _architect);
        _grantRole(FEE_MANAGER_ROLE, msg.sender);
    }

    // ==================== Treasury Management ====================
    /**
     * @notice Fund the treasury with tokens (called by FEE_MANAGER_ROLE).
     * @param amount Amount of tokens to transfer from caller to this contract.
     */
    function fundTreasury(uint256 amount) external onlyFeeManager nonReentrant whenNotPaused {
        require(amount > 0, "Amount zero");
        require(token.transferFrom(msg.sender, address(this), amount), "Transfer failed");
        treasuryBalance += amount;
        emit TreasuryFunded(msg.sender, amount);
    }

    /**
     * @notice Withdraw tokens from treasury (only ARCHITECT_ROLE).
     * @param amount Amount to withdraw.
     * @param to Recipient address.
     */
    function withdrawTreasury(uint256 amount, address to) external onlyArchitect nonReentrant whenNotPaused {
        require(amount > 0 && amount <= treasuryBalance, "Invalid amount");
        require(to != address(0), "Invalid address");
        treasuryBalance -= amount;
        require(token.transfer(to, amount), "Transfer failed");
        emit TreasuryWithdrawn(to, amount);
    }

    // ==================== Core Transfer Logic ====================
    /**
     * @notice Transfer tokens with competitive fee game.
     * @param recipient Address receiving the tokens.
     * @param amount Amount of tokens to transfer (principal).
     *
     * Game rules:
     * - Sender pays principal + fee (fee = amount * feeBasisPoints / 10000).
     * - Fee is immediately sent to the architect.
     * - Principal is sent to the recipient.
     * - If amount > lastRecordAmount, the sender receives a bonus equal to the fee from the treasury,
     *   and the record is updated to the new amount.
     */
    function transferWithFee(address recipient, uint256 amount) external nonReentrant whenNotPaused {
        require(recipient != address(0), "Invalid recipient");
        require(amount > 0, "Amount zero");

        uint256 fee = (amount * feeBasisPoints) / 10000;
        uint256 total = amount + fee;

        // Transfer total from sender to this contract
        require(token.transferFrom(msg.sender, address(this), total), "TransferFrom failed");

        // Send principal to recipient
        require(token.transfer(recipient, amount), "Transfer to recipient failed");

        // Send fee to architect
        require(token.transfer(architect, fee), "Transfer to architect failed");

        // Determine bonus
        bool bonusPaid = false;
        uint256 bonusAmount = 0;
        if (amount > lastRecordAmount) {
            bonusAmount = fee; // bonus equals the fee amount
            if (treasuryBalance >= bonusAmount) {
                treasuryBalance -= bonusAmount;
                require(token.transfer(msg.sender, bonusAmount), "Bonus transfer failed");
                bonusPaid = true;
            }
            lastRecordAmount = amount;
            emit RecordUpdated(lastRecordAmount);
        }

        emit TransferWithFee(msg.sender, recipient, amount, fee, bonusPaid, bonusAmount);
    }

    // ==================== Fee Configuration (with timelock) ====================
    function proposeFee(uint256 newFeeBasisPoints) external onlyGovernor {
        require(newFeeBasisPoints <= MAX_FEE_BASIS_POINTS, "Fee too high");
        pendingFee = PendingFee(newFeeBasisPoints, block.timestamp);
        emit FeeProposed(newFeeBasisPoints, block.timestamp);
    }

    function executeFee() external onlyGovernor {
        require(pendingFee.value != 0, "No pending fee");
        require(block.timestamp >= pendingFee.timestamp + TIMELOCK_DELAY, "Timelock not expired");
        feeBasisPoints = pendingFee.value;
        delete pendingFee;
        emit FeeExecuted(feeBasisPoints);
    }

    // ==================== Architect Address Change (with timelock) ====================
    function proposeArchitect(address newArchitect) external onlyGovernor {
        require(newArchitect != address(0), "Invalid address");
        pendingArchitect = PendingArchitect(newArchitect, block.timestamp);
        emit ArchitectProposed(newArchitect, block.timestamp);
    }

    function executeArchitect() external onlyGovernor {
        require(pendingArchitect.value != address(0), "No pending architect");
        require(block.timestamp >= pendingArchitect.timestamp + TIMELOCK_DELAY, "Timelock not expired");
        address oldArchitect = architect;
        architect = pendingArchitect.value;
        _revokeRole(ARCHITECT_ROLE, oldArchitect);
        _grantRole(ARCHITECT_ROLE, architect);
        delete pendingArchitect;
        emit ArchitectExecuted(architect);
    }

    // ==================== Pausable ====================
    function pause() external onlyGovernor {
        _pause();
    }

    function unpause() external onlyGovernor {
        _unpause();
    }

    // ==================== View Functions ====================
    function getTreasuryBalance() external view returns (uint256) {
        return treasuryBalance;
    }

    function getLastRecord() external view returns (uint256) {
        return lastRecordAmount;
    }
}
