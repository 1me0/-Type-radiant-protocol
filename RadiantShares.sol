// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";   // v5 path
import "@openzeppelin/contracts/utils/Pausable.sol";           // v5 path

/**
 * @title RadiantShares
 * @dev ERC20 token with:
 *      - Max supply (100M)
 *      - 50/50 mint split (architect / treasury)
 *      - Configurable transfer tax (≤5%) to architect (perpetual income)
 *      - Tax exempt for architect and treasury wallets
 *      - Timelocked mint proposals (2 days)
 *      - Timelocked address changes (2 days)
 *      - Pausable (emergency stop)
 *      - Admin role cannot be renounced
 */
contract RadiantShares is ERC20, AccessControl, ReentrancyGuard, Pausable {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant GOVERNOR_ROLE = keccak256("GOVERNOR_ROLE");

    // … (the rest of the contract remains identical) … 
    // (include all the state variables, constructor, functions as in the original)
}
