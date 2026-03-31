// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract ArchitectFee {
    IERC20 public token;
    address public architect;
    uint256 public lastArchitectTransactionAmount;

    event TransferWithFee(
        address indexed from,
        address indexed to,
        uint256 amount,
        uint256 fee,
        bool feeToSender
    );

    constructor(address _token, address _architect) {
        token = IERC20(_token);
        architect = _architect;
        lastArchitectTransactionAmount = 0;
    }

    /**
     * @dev Transfer tokens from sender to recipient.
     * The sender must have approved this contract to spend `amount + fee`.
     * Fee = amount * 50 / 100.
     * If amount > lastArchitectTransactionAmount, the fee is returned to sender (reward).
     * Otherwise, the fee goes to the architect.
     * The architect's last transaction record is updated if amount > lastArchitectTransactionAmount.
     */
    function transferWithFee(address recipient, uint256 amount) external {
        require(recipient != address(0), "Invalid recipient");
        require(amount > 0, "Amount must be positive");

        uint256 fee = (amount * 50) / 100; // 50% fee
        uint256 totalToSpend = amount + fee;

        // Transfer tokens from sender to contract
        require(
            token.transferFrom(msg.sender, address(this), totalToSpend),
            "TransferFrom failed"
        );

        // Determine where the fee goes
        bool feeToSender = false;
        if (amount > lastArchitectTransactionAmount) {
            feeToSender = true;
            // Update record
            lastArchitectTransactionAmount = amount;
        }

        // Transfer amount to recipient
        token.transfer(recipient, amount);

        // Transfer fee to appropriate destination
        if (feeToSender) {
            token.transfer(msg.sender, fee); // send fee back to sender (reward)
        } else {
            token.transfer(architect, fee); // send fee to architect
        }

        emit TransferWithFee(msg.sender, recipient, amount, fee, feeToSender);
    }

    /**
     * @dev Update the architect address (only callable by current architect)
     */
    function setArchitect(address newArchitect) external {
        require(msg.sender == architect, "Only architect");
        architect = newArchitect;
    }
}
---

## 2. ArchitectFee.sol (Smart Contract)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

contract ArchitectFee {
    IERC20 public token;
    address public architect;
    uint256 public lastArchitectTransactionAmount;

    event TransferWithFee(
        address indexed from,
        address indexed to,
        uint256 amount,
        uint256 fee,
        bool feeToSender
    );

    constructor(address _token, address _architect) {
        token = IERC20(_token);
        architect = _architect;
        lastArchitectTransactionAmount = 0;
    }

    /**
     * @dev Transfer tokens from sender to recipient.
     * The sender must have approved this contract to spend `amount + fee`.
     * Fee = amount * 50 / 100.
     * If amount > lastArchitectTransactionAmount, the fee is returned to sender (reward).
     * Otherwise, the fee goes to the architect.
     * The architect's last transaction record is updated if amount > lastArchitectTransactionAmount.
     */
    function transferWithFee(address recipient, uint256 amount) external {
        require(recipient != address(0), "Invalid recipient");
        require(amount > 0, "Amount must be positive");

        uint256 fee = (amount * 50) / 100; // 50% fee
        uint256 totalToSpend = amount + fee;

        // Transfer tokens from sender to contract
        require(
            token.transferFrom(msg.sender, address(this), totalToSpend),
            "TransferFrom failed"
        );

        // Determine where the fee goes
        bool feeToSender = false;
        if (amount > lastArchitectTransactionAmount) {
            feeToSender = true;
            lastArchitectTransactionAmount = amount;
        }

        // Transfer amount to recipient
        token.transfer(recipient, amount);

        // Transfer fee to appropriate destination
        if (feeToSender) {
            token.transfer(msg.sender, fee); // send fee back to sender (reward)
        } else {
            token.transfer(architect, fee); // send fee to architect
        }

        emit TransferWithFee(msg.sender, recipient, amount, fee, feeToSender);
    }

    /**
     * @dev Update the architect address (only callable by current architect)
     */
    function setArchitect(address newArchitect) external {
        require(msg.sender == architect, "Only architect");
        architect = newArchitect;
    }
}
