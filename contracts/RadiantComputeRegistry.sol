// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title RadiantComputeRegistry
 * @notice Tracks cumulative computing value and mints RAD tokens when thresholds are crossed.
 *         For each unit of 100 computing value, 50 RAD are minted to the architect and 50 RAD to the system vault.
 *
 * Roles:
 * - DEFAULT_ADMIN_ROLE: can update architect/vault addresses and withdraw accidentally sent tokens.
 * - RECORDER_ROLE: can record computing value (e.g., from an oracle or monitoring service).
 */
contract RadiantComputeRegistry is ERC20, AccessControl {
    bytes32 public constant RECORDER_ROLE = keccak256("RECORDER_ROLE");

    address public architect;
    address public vault;

    uint256 public constant UNIT = 100;               // One unit = 100 compute value
    uint256 public constant ARCHITECT_SHARE = 50;     // 50 RAD per unit to architect
    uint256 public constant VAULT_SHARE = 50;         // 50 RAD per unit to vault

    uint256 public totalComputed;                     // Cumulative compute value
    uint256 public lastMintedUnit;                    // Last unit index for which tokens were minted (1‑based)

    event ComputationRecorded(uint256 amount, uint256 newTotal);
    event TokensMinted(uint256 unitStart, uint256 unitEnd, uint256 architectMint, uint256 vaultMint);
    event ArchitectUpdated(address indexed oldArchitect, address indexed newArchitect);
    event VaultUpdated(address indexed oldVault, address indexed newVault);

    constructor(address _architect, address _vault) ERC20("Radiant Share", "RAD") {
        require(_architect != address(0), "Invalid architect");
        require(_vault != address(0), "Invalid vault");
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

        uint256 oldUnits = oldTotal / UNIT;
        uint256 newUnits = totalComputed / UNIT;
        if (newUnits > oldUnits) {
            // Mint tokens for all new units from oldUnits+1 to newUnits
            _mintForUnits(oldUnits + 1, newUnits);
            lastMintedUnit = newUnits;
        }
    }

    /**
     * @dev Internal function to mint tokens for a range of unit indices.
     * @param startUnit The first unit index (1‑based).
     * @param endUnit The last unit index inclusive.
     */
    function _mintForUnits(uint256 startUnit, uint256 endUnit) internal {
        uint256 unitsToMint = endUnit - startUnit + 1;
        uint256 architectTotal = unitsToMint * ARCHITECT_SHARE;
        uint256 vaultTotal = unitsToMint * VAULT_SHARE;

        if (architectTotal > 0) {
            _mint(architect, architectTotal);
        }
        if (vaultTotal > 0) {
            _mint(vault, vaultTotal);
        }
        emit TokensMinted(startUnit, endUnit, architectTotal, vaultTotal);
    }

    /**
     * @notice Set a new architect address (only admin).
     * @param newArchitect The new architect address.
     */
    function setArchitect(address newArchitect) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(newArchitect != address(0), "Invalid address");
        address old = architect;
        architect = newArchitect;
        emit ArchitectUpdated(old, newArchitect);
    }

    /**
     * @notice Set a new vault address (only admin).
     * @param newVault The new vault address.
     */
    function setVault(address newVault) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(newVault != address(0), "Invalid address");
        address old = vault;
        vault = newVault;
        emit VaultUpdated(old, newVault);
    }

    /**
     * @notice Get the next pending unit (the next unit that would be minted after current totalComputed).
     * @return The next unit index (1‑based), or 0 if totalComputed is below UNIT.
     */
    function getNextPendingUnit() external view returns (uint256) {
        return (totalComputed / UNIT) + 1;
    }

    /**
     * @notice Allow the admin to withdraw accidentally sent tokens (not RAD) from this contract.
     * @param tokenAddr The address of the token to withdraw (cannot be this contract's own token).
     * @param amount The amount to withdraw.
     */
    function withdrawTokens(address tokenAddr, uint256 amount) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(tokenAddr != address(this), "Cannot withdraw RAD");
        require(amount > 0, "Amount must be positive");
        IERC20 token = IERC20(tokenAddr);
        require(token.transfer(msg.sender, amount), "Transfer failed");
    }
}
