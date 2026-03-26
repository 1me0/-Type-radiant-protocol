// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract RadiantToken is ERC20, Ownable {
    mapping(bytes32 => bool) public processedHashes;
    uint256 public constant RADIANCE_REWARD = 10 * 10**18; // 10 $RAD

    constructor() ERC20("Radiant Protocol", "RAD") Ownable(msg.sender) {}

    // The Master Formula in Code: Validating Presence
    function participateGenesis(bytes32 proofHash) external {
        require(!processedHashes[proofHash], "Presence already recorded.");
        
        processedHashes[proofHash] = true;
        _mint(msg.sender, RADIANCE_REWARD);
    }
}
