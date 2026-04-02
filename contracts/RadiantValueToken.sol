// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title ArchitectFeeV2
 * @notice Implements a 50% fee on token transfers, with a bonus reward for users
 *         who exceed the architect's last recorded transaction amount.
 *
 * The user pays the principal + 50% fee. The fee always goes to the architect.
 * If the principal amount is greater than the last recorded transaction,
 * the user receives a bonus reward equal to 50% of the principal (from treasury).
 * The architect's record is updated to the new principal amount.
 */
contract ArchitectFeeV2 is AccessControl {
    bytes32 public constant TREASURY_ADMIN = keccak256("TREASURY_ADMIN");

    IERC20 public token;
    address public architect;
    uint256 public lastArchitectTransactionAmount;

    event TransferWithBonus(
        address indexed sender,
        address indexed recipient,
        uint256 amount,
        uint256 fee,
        uint256 reward
    );
    event TreasuryFunded(address indexed funder, uint256 amount);
    event ArchitectUpdated(address indexed newArchitect);
    event TreasuryAdminAdded(address indexed admin);

    constructor(address _token, address _architect) {
        require(_token != address(0), "Invalid token");
        require(_architect != address(0), "Invalid architect");
        token = IERC20(_token);
        architect = _architect;
        lastArchitectTransactionAmount = 0;
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(TREASURY_ADMIN, msg.sender);
    }

    /**
     * @dev Add a treasury admin (can fund the treasury)
     */
    function addTreasuryAdmin(address admin) external onlyRole(DEFAULT_ADMIN_ROLE) {
        grantRole(TREASURY_ADMIN, admin);
        emit TreasuryAdminAdded(admin);
    }

    /**
     * @dev Fund the treasury with tokens (only treasury admin)
     */
    function fundTreasury(uint256 amount) external onlyRole(TREASURY_ADMIN) {
        require(token.transferFrom(msg.sender, address(this), amount), "Transfer failed");
        emit TreasuryFunded(msg.sender, amount);
    }

    /**
     * @dev Transfer tokens with fee and potential bonus reward.
     * The sender must approve this contract to spend `amount + fee` tokens.
     */
    function transferWithBonus(address recipient, uint256 amount) external {
        require(recipient != address(0), "Invalid recipient");
        require(amount > 0, "Amount must be positive");

        uint256 fee = amount / 2;          // 50% fee
        uint256 totalRequired = amount + fee;

        // Transfer totalRequired from sender to this contract
        require(token.transferFrom(msg.sender, address(this), totalRequired), "TransferFrom failed");

        // Send principal to recipient
        token.transfer(recipient, amount);

        // Send fee to architect
        token.transfer(architect, fee);

        // Determine reward
        uint256 reward = 0;
        if (amount > lastArchitectTransactionAmount) {
            reward = amount / 2;            // Bonus reward equal to 50% of principal
            lastArchitectTransactionAmount = amount;
        }

        // If a reward is due, send it from treasury to sender
        if (reward > 0) {
            require(token.balanceOf(address(this)) >= reward, "Insufficient treasury balance");
            token.transfer(msg.sender, reward);
        }

        emit TransferWithBonus(msg.sender, recipient, amount, fee, reward);
    }

    /**
     * @dev Update the architect address (only admin)
     */
    function setArchitect(address newArchitect) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(newArchitect != address(0), "Invalid address");
        architect = newArchitect;
        emit ArchitectUpdated(newArchitect);
    }

    /**
     * @dev Withdraw tokens from treasury (only admin, for emergencies)
     */
    function withdrawTreasury(uint256 amount, address to) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(to != address(0), "Invalid address");
        require(token.transfer(to, amount), "Transfer failed");
    }
}
