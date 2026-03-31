// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract Radiant is ERC20, Ownable {
    uint256 public constant POINTS_TO_RAD_RATIO = 10; // 1000 points = 100 RAD
    uint256 public protocolFeePercent = 1; // 1% Sovereign Fee

    event PointsConverted(address indexed user, uint256 points, uint256 radAmount);

    constructor() ERC20("Radiant Protocol", "RAD") Ownable(msg.sender) {
        _mint(msg.sender, 1000000 * 10**decimals()); // Initial Supply
    }

    // The Bridge: Converts Intelligence Points to RAD Tokens
    function convertPointsToRAD(uint256 points) external {
        require(points >= 1000, "Minimum 1000 points required");
        uint256 amountToMint = (points / POINTS_TO_RAD_RATIO) * 10**decimals();
        
        _mint(msg.sender, amountToMint);
        emit PointsConverted(msg.sender, points, amountToMint);
    }

    // Sovereign Fee Logic: Collects 1% on transfers
    function transfer(address to, uint256 amount) public override returns (bool) {
        uint256 fee = (amount * protocolFeePercent) / 100;
        uint256 finalAmount = amount - fee;
        
        _transfer(_msgSender(), owner(), fee); // Fee goes to Radiant Architect
        _transfer(_msgSender(), to, finalAmount);
        return true;
    }
}
