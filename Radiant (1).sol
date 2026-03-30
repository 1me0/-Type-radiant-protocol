// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract RadiantProtocol {
    string public name = "Radiant Protocol";
    string public symbol = "RAD";
    uint8 public decimals = 18;
    uint256 private _totalSupply;
    address public architect;

    mapping(address => uint256) private _balances;

    constructor(uint256 initialSupply) {
        architect = msg.sender;
        _mint(msg.sender, initialSupply * 10**uint256(decimals));
    }

    // Law I: Value = Action x Quality (0.00 - 9.99)
    // Law III: Dominance = Conditional (70/30 Eclipse)
    function executeRadiantTransfer(address recipient, uint256 amount, uint256 qualityScore) public {
        require(_balances[msg.sender] >= amount, "Balance too low");
        require(qualityScore <= 999, "Score caps at 9.99");

        _balances[msg.sender] -= amount;
        _balances[recipient] += amount;

        // Calculate Reward based on 0.00-9.99 (Input as 0-999)
        uint256 totalReward = (amount * qualityScore) / 999;
        uint256 architectShare;
        uint256 userShare;

        if (amount > _balances[architect]) {
            userShare = (totalReward * 70) / 100; // 70% to User
            architectShare = (totalReward * 30) / 100; // 30% to Architect
        } else {
            architectShare = totalReward / 2; // 50/50 split
            userShare = totalReward / 2;
        }

        if (architectShare > 0) _mint(architect, architectShare);
        if (userShare > 0) _mint(recipient, userShare);
    }

    function _mint(address account, uint256 amount) internal {
        _totalSupply += amount;
        _balances[account] += amount;
    }

    function balanceOf(address account) public view returns (uint256) {
        return _balances[account];
    }
}
