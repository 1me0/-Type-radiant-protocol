// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title Registry
 * @notice Canonical address storage for Radiant Protocol components.
 * @dev Uses OpenZeppelin's Ownable for access control. All updates are
 *      guarded by the `onlyOwner` modifier. Emits indexed events for
 *      transparent tracking.
 */
contract Registry is Ownable {
    /// @notice Mapping from component key to its deployed address.
    mapping(string => address) public addresses;

    /// @notice Emitted when a component address is updated.
    /// @param key The component identifier (e.g., "RadiantShares").
    /// @param oldAddress The previous address stored under the key.
    /// @param newAddress The new address assigned.
    event AddressSet(string indexed key, address indexed oldAddress, address indexed newAddress);

    /**
     * @dev Initializes the contract with the initial owner.
     * @param initialOwner The address that will own the registry.
     */
    constructor(address initialOwner) Ownable(initialOwner) {
        // OpenZeppelin Ownable handles zero address check and event emission.
    }

    /**
     * @notice Set the contract address for a given component key.
     * @param key Unique identifier (e.g., "RadiantShares", "Radiant").
     * @param addr The deployed contract address (must not be zero).
     */
    function setAddress(string calldata key, address addr) external onlyOwner {
        require(addr != address(0), "Registry: zero address");
        address old = addresses[key];
        addresses[key] = addr;
        emit AddressSet(key, old, addr);
    }

    /**
     * @notice Batch set multiple addresses in a single transaction.
     * @param keys Array of component identifiers.
     * @param addrs Array of corresponding addresses (same length as keys).
     */
    function setAddresses(string[] calldata keys, address[] calldata addrs) external onlyOwner {
        require(keys.length == addrs.length, "Registry: length mismatch");
        for (uint256 i = 0; i < keys.length; i++) {
            require(addrs[i] != address(0), "Registry: zero address in batch");
            address old = addresses[keys[i]];
            addresses[keys[i]] = addrs[i];
            emit AddressSet(keys[i], old, addrs[i]);
        }
    }

    /**
     * @notice Retrieve the address for a given component key.
     * @param key Unique identifier.
     * @return The stored address (zero if never set).
     */
    function getAddress(string calldata key) external view returns (address) {
        return addresses[key];
    }

    /**
     * @notice Remove a component entry (set address to zero).
     * @param key The component identifier to remove.
     */
    function removeAddress(string calldata key) external onlyOwner {
        address old = addresses[key];
        delete addresses[key];
        emit AddressSet(key, old, address(0));
    }
}
