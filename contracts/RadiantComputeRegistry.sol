// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title RadiantComputeRegistry
 * @notice Tracks cumulative computing value and mints RAD tokens when thresholds are crossed.
 *         For each unit of 100 computing value, the first 50 RAD are minted to the architect,
 *         the next 50 RAD are minted to the system vault.
 */
contract RadiantComputeRegistry is ERC20, AccessControl {
    bytes32 public constant RECORDER_ROLE = keccak256("RECORDER_ROLE");
    address public architect;
    address public vault;

    uint256 public constant UNIT = 100;          // One unit = 100 compute value
    uint256 public constant ARCHITECT_SHARE = 50; // 50% of unit
    uint256 public constant VAULT_SHARE = 50;     // remaining 50%

    uint256 public totalComputed;                // Cumulative compute value
    uint256 public lastMintedUnit;               // Last unit index for which tokens were minted

    event ComputationRecorded(uint256 amount, uint256 newTotal);
    event TokensMinted(uint256 unitStart, uint256 unitEnd, uint256 architectMint, uint256 vaultMint);

    constructor(address _architect, address _vault) ERC20("Radiant Share", "RAD") {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(RECORDER_ROLE, msg.sender);
        architect = _architect;
        vault = _vault;
        totalComputed = 0;
        lastMintedUnit = 0;
    }

    /**
     * @notice Record new computing value.
     * @param amount The amount of computing value detected (e.g., percentage of capacity).
     */
    function recordComputation(uint256 amount) external onlyRole(RECORDER_ROLE) {
        require(amount > 0, "Amount must be positive");
        uint256 oldTotal = totalComputed;
        totalComputed += amount;
        emit ComputationRecorded(amount, totalComputed);

        // Determine how many full units have been completed since last mint
        uint256 oldUnits = oldTotal / UNIT;
        uint256 newUnits = totalComputed / UNIT;
        if (newUnits > oldUnits) {
            uint256 unitsToMint = newUnits - oldUnits;
            _mintForUnits(oldUnits + 1, newUnits);
        }
    }

    /**
     * @dev Internal function to mint tokens for a range of unit indices.
     * @param startUnit The first unit index (1‑based).
     * @param endUnit The last unit index inclusive.
     */
    function _mintForUnits(uint256 startUnit, uint256 endUnit) internal {
        uint256 architectTotal = 0;
        uint256 vaultTotal = 0;
        for (uint256 u = startUnit; u <= endUnit; u++) {
            architectTotal += ARCHITECT_SHARE;
            vaultTotal += VAULT_SHARE;
        }
        if (architectTotal > 0) {
            _mint(architect, architectTotal);
        }
        if (vaultTotal > 0) {
            _mint(vault, vaultTotal);
        }
        emit TokensMinted(startUnit, endUnit, architectTotal, vaultTotal);
    }

    /**
     * @dev Set a new architect address (only admin).
     */
    function setArchitect(address newArchitect) external onlyRole(DEFAULT_ADMIN_ROLE) {
        architect = newArchitect;
    }

    /**
     * @dev Set a new vault address (only admin).
     */
    function setVault(address newVault) external onlyRole(DEFAULT_ADMIN_ROLE) {
        vault = newVault;
    }
}
