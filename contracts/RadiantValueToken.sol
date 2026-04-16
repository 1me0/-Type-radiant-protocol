// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";

/**
 * @title ArchitectFeeV2
 * @notice Competitive fee game with 50% fee, record‑breaking bonus, and treasury management.
 */
contract ArchitectFeeV2 is AccessControl, ReentrancyGuard, Pausable {
    bytes32 public constant TREASURY_ADMIN = keccak256("TREASURY_ADMIN");

    IERC20 public token;
    address public architect;
    uint256 public lastArchitectTransactionAmount;

    // Timelock for architect change
    struct PendingArchitect {
        address value;
        uint256 timestamp;
    }
    PendingArchitect public pendingArchitect;
    uint256 public constant ARCHITECT_TIMELOCK = 2 days;

    // Treasury withdrawal limit
    uint256 public maxWithdrawalPerTx;
    uint256 public constant DEFAULT_MAX_WITHDRAWAL = 10_000 * 10**18; // 10k tokens

    event TransferWithBonus(
        address indexed sender,
        address indexed recipient,
        uint256 amount,
        uint256 fee,
        uint256 reward
    );
    event TreasuryFunded(address indexed funder, uint256 amount);
    event ArchitectProposed(address indexed newArchitect, uint256 timestamp);
    event ArchitectUpdated(address indexed newArchitect);
    event TreasuryAdminAdded(address indexed admin);
    event TreasuryWithdrawn(address indexed to, uint256 amount);
    event MaxWithdrawalUpdated(uint256 newLimit);
    event Paused(address account);
    event Unpaused(address account);

    constructor(address _token, address _architect) {
        require(_token != address(0), "Invalid token");
        require(_architect != address(0), "Invalid architect");
        token = IERC20(_token);
        architect = _architect;
        lastArchitectTransactionAmount = 0;
        maxWithdrawalPerTx = DEFAULT_MAX_WITHDRAWAL;
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(TREASURY_ADMIN, msg.sender);
    }

    modifier onlyTreasuryAdmin() {
        require(hasRole(TREASURY_ADMIN, msg.sender), "Not treasury admin");
        _;
    }

    // ==================== Treasury Management ====================
    function addTreasuryAdmin(address admin) external onlyRole(DEFAULT_ADMIN_ROLE) {
        grantRole(TREASURY_ADMIN, admin);
        emit TreasuryAdminAdded(admin);
    }

    function fundTreasury(uint256 amount) external onlyTreasuryAdmin whenNotPaused {
        require(amount > 0, "Amount zero");
        require(token.transferFrom(msg.sender, address(this), amount), "Transfer failed");
        emit TreasuryFunded(msg.sender, amount);
    }

    function withdrawTreasury(uint256 amount, address to) external onlyRole(DEFAULT_ADMIN_ROLE) whenNotPaused {
        require(to != address(0), "Invalid address");
        require(amount > 0 && amount <= maxWithdrawalPerTx, "Amount exceeds limit");
        require(token.balanceOf(address(this)) >= amount, "Insufficient treasury");
        require(token.transfer(to, amount), "Transfer failed");
        emit TreasuryWithdrawn(to, amount);
    }

    function setMaxWithdrawal(uint256 newLimit) external onlyRole(DEFAULT_ADMIN_ROLE) {
        maxWithdrawalPerTx = newLimit;
        emit MaxWithdrawalUpdated(newLimit);
    }

    // ==================== Core Transfer Logic ====================
    function transferWithBonus(address recipient, uint256 amount) external nonReentrant whenNotPaused {
        require(recipient != address(0), "Invalid recipient");
        require(amount > 0, "Amount must be positive");

        uint256 fee = amount / 2;          // 50% fee
        uint256 totalRequired = amount + fee;

        require(token.transferFrom(msg.sender, address(this), totalRequired), "TransferFrom failed");

        token.transfer(recipient, amount);
        token.transfer(architect, fee);

        uint256 reward = 0;
        if (amount > lastArchitectTransactionAmount) {
            reward = amount / 2;
            lastArchitectTransactionAmount = amount;
        }

        if (reward > 0) {
            require(token.balanceOf(address(this)) >= reward, "Insufficient treasury balance");
            token.transfer(msg.sender, reward);
        }

        emit TransferWithBonus(msg.sender, recipient, amount, fee, reward);
    }

    // ==================== Architect Change with Timelock ====================
    function proposeArchitect(address newArchitect) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(newArchitect != address(0), "Invalid address");
        pendingArchitect = PendingArchitect(newArchitect, block.timestamp);
        emit ArchitectProposed(newArchitect, block.timestamp);
    }

    function executeArchitect() external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(pendingArchitect.value != address(0), "No pending architect");
        require(block.timestamp >= pendingArchitect.timestamp + ARCHITECT_TIMELOCK, "Timelock not expired");
        architect = pendingArchitect.value;
        delete pendingArchitect;
        emit ArchitectUpdated(architect);
    }

    // ==================== Pausable ====================
    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _pause();
        emit Paused(msg.sender);
    }

    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
        emit Unpaused(msg.sender);
    }

    // ==================== View Functions ====================
    function getTreasuryBalance() external view returns (uint256) {
        return token.balanceOf(address(this));
    }
}
