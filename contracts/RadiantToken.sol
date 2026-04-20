// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";

/**
 * @title RadiantToken
 * @notice ERC20 token with staking, vesting, reputation, and 50/50 reward split between user and architect.
 *
 * Roles:
 * - DEFAULT_ADMIN_ROLE: can manage vesting, reputation, set architect, pause/unpause.
 * - MINTER_ROLE: can mint tokens (optional, not used directly in this contract; minting is done via verifyProof).
 * - RELAYER_ROLE: can verify proofs and slash users.
 *
 * Features:
 * - Staking: users can deposit tokens to earn reputation and rewards.
 * - Vesting: admin can create linear vesting schedules for users.
 * - Reputation: can be set by admin and increased automatically on proof verification.
 * - Proof verification: relayers can reward users with a 50/50 split between user and architect.
 * - Slashing: relayers can slash staked tokens from malicious users.
 * - Pausable: emergency stop for staking, unstaking, proof verification, and slashing.
 * - Max supply: 100 million tokens (enforced in _mint).
 */
contract RadiantToken is ERC20, AccessControl, ReentrancyGuard, Pausable {
    bytes32 public constant RELAYER_ROLE = keccak256("RELAYER_ROLE");
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");

    uint256 public constant MAX_SUPPLY = 100_000_000 * 10**18; // 100 million tokens
    uint256 public constant ARCHITECT_FEE_BPS = 5000; // 50%

    address public architect;

    struct UserInfo {
        uint256 stake;
        uint256 reputation;
        uint256 rewards;
    }
    mapping(address => UserInfo) public users;

    struct VestingSchedule {
        uint256 totalAmount;
        uint256 start;
        uint256 duration;
        uint256 claimed;
    }
    mapping(address => VestingSchedule) public vesting;
    uint256 public lockedBalance;

    // Events
    event Staked(address indexed user, uint256 amount);
    event Unstaked(address indexed user, uint256 amount);
    event ReputationUpdated(address indexed user, uint256 weight);
    event VestingCreated(address indexed user, uint256 amount, uint256 duration);
    event RewardDistributed(address indexed user, uint256 userAmount, uint256 architectAmount);
    event ProofVerified(address indexed user, uint256 reward);
    event Slashed(address indexed user, uint256 amount);
    event Claimed(address indexed user, uint256 amount);
    event ArchitectUpdated(address indexed oldArchitect, address indexed newArchitect);

    constructor(
        string memory name,
        string memory symbol,
        address _architect,
        uint256 initialSupply
    ) ERC20(name, symbol) {
        require(_architect != address(0), "Invalid architect");
        require(initialSupply <= MAX_SUPPLY, "Initial supply exceeds max supply");
        architect = _architect;
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(RELAYER_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
        _mint(msg.sender, initialSupply);
    }

    // ==================== Modifiers ====================
    modifier onlyRelayer() {
        require(hasRole(RELAYER_ROLE, msg.sender), "Caller is not relayer");
        _;
    }

    modifier onlyMinter() {
        require(hasRole(MINTER_ROLE, msg.sender), "Caller is not minter");
        _;
    }

    // ==================== Overrides ====================
    function _mint(address account, uint256 amount) internal virtual override {
        require(totalSupply() + amount <= MAX_SUPPLY, "Exceeds max supply");
        super._mint(account, amount);
    }

    // ==================== Staking ====================
    /**
     * @dev Stake tokens to receive reputation and rewards.
     * @param amount Amount of tokens to stake.
     */
    function stake(uint256 amount) external nonReentrant whenNotPaused {
        require(amount > 0, "Amount zero");
        _transfer(msg.sender, address(this), amount);
        users[msg.sender].stake += amount;
        emit Staked(msg.sender, amount);
    }

    /**
     * @dev Unstake tokens from the contract.
     * @param amount Amount to unstake (cannot exceed staked balance).
     */
    function unstake(uint256 amount) external nonReentrant whenNotPaused {
        require(amount > 0 && amount <= users[msg.sender].stake, "Invalid amount");
        _transfer(address(this), msg.sender, amount);
        users[msg.sender].stake -= amount;
        emit Unstaked(msg.sender, amount);
    }

    // ==================== Vesting ====================
    /**
     * @dev Create a vesting schedule for a user. Tokens are taken from the caller's balance.
     * @param user Address of the beneficiary.
     * @param amount Total amount to vest.
     * @param durationSeconds Duration of the vesting period in seconds.
     */
    function createVesting(address user, uint256 amount, uint256 durationSeconds) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(amount > 0, "Amount zero");
        require(durationSeconds > 0, "Duration must be positive");
        require(amount <= balanceOf(msg.sender), "Insufficient balance");
        _transfer(msg.sender, address(this), amount);
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
     * @dev Claim vested tokens.
     */
    function claimVested() external nonReentrant {
        VestingSchedule storage v = vesting[msg.sender];
        require(v.totalAmount > 0, "No vesting");
        uint256 elapsed = block.timestamp - v.start;
        uint256 vested = (v.totalAmount * elapsed) / v.duration;
        uint256 claimable = vested - v.claimed;
        require(claimable > 0, "Nothing to claim");
        v.claimed += claimable;
        lockedBalance -= claimable;
        _transfer(address(this), msg.sender, claimable);
        emit Claimed(msg.sender, claimable);
    }

    // ==================== Reputation ====================
    /**
     * @dev Set a user's reputation (admin only).
     * @param user Address of the user.
     * @param weight New reputation value.
     */
    function setReputation(address user, uint256 weight) external onlyRole(DEFAULT_ADMIN_ROLE) {
        users[user].reputation = weight;
        emit ReputationUpdated(user, weight);
    }

    // ==================== Proof Verification (Reward with 50/50 split) ====================
    /**
     * @dev Reward a user for a verified proof. Called by relayer.
     * @param user Address of the user.
     * @param baseReward Total reward amount (before split).
     */
    function verifyProof(address user, uint256 baseReward) external onlyRelayer whenNotPaused {
        require(baseReward > 0, "Reward zero");
        uint256 architectShare = (baseReward * ARCHITECT_FEE_BPS) / 10000;
        uint256 userShare = baseReward - architectShare;

        if (userShare > 0) {
            _mint(user, userShare);
            users[user].rewards += userShare;
        }
        if (architectShare > 0) {
            _mint(architect, architectShare);
        }
        users[user].reputation += 10;
        emit RewardDistributed(user, userShare, architectShare);
        emit ProofVerified(user, baseReward);
    }

    // ==================== Slashing ====================
    /**
     * @dev Slash a user's staked tokens (burn them). Called by relayer.
     * @param user Address of the user.
     * @param amount Amount to slash (cannot exceed staked balance).
     */
    function slash(address user, uint256 amount) external onlyRelayer whenNotPaused {
        require(amount > 0 && amount <= users[user].stake, "Invalid slash amount");
        users[user].stake -= amount;
        _burn(address(this), amount); // burned tokens are removed from supply
        emit Slashed(user, amount);
    }

    // ==================== Admin ====================
    /**
     * @dev Update the architect address (admin only).
     * @param newArchitect New architect address.
     */
    function setArchitect(address newArchitect) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(newArchitect != address(0), "Invalid address");
        address old = architect;
        architect = newArchitect;
        emit ArchitectUpdated(old, newArchitect);
    }

    function pause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _pause();
    }

    function unpause() external onlyRole(DEFAULT_ADMIN_ROLE) {
        _unpause();
    }

    // ==================== Utility ====================
    /**
     * @dev Get user's staking, reputation, and rewards information.
     * @param user Address of the user.
     * @return stake Staked amount.
     * @return reputation Reputation score.
     * @return rewards Total rewards earned.
     */
    function getUserInfo(address user) external view returns (uint256 stake, uint256 reputation, uint256 rewards) {
        UserInfo memory u = users[user];
        return (u.stake, u.reputation, u.rewards);
    }
}
