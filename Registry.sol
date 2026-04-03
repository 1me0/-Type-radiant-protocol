// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title Registry
 * @notice Stores canonical contract addresses for the Radiant Protocol.
 *         Only the owner can update addresses. Designed to be transparent and safe.
 */
contract Registry {
    address public owner;
    mapping(string => address) public addresses;

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event AddressSet(string indexed key, address indexed oldAddress, address indexed newAddress);

    constructor() {
        owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Registry: not owner");
        _;
    }

    /**
     * @dev Set the contract address for a given key.
     * @param key Unique identifier (e.g., "RadiantShares", "Radiant", "ArchitectFee")
     * @param addr The contract address (cannot be zero)
     */
    function setAddress(string calldata key, address addr) external onlyOwner {
        require(addr != address(0), "Registry: zero address");
        address old = addresses[key];
        addresses[key] = addr;
        emit AddressSet(key, old, addr);
    }

    /**
     * @dev Get the contract address for a given key.
     * @param key Unique identifier
     * @return The stored address (may be zero if not set)
     */
    function getAddress(string calldata key) external view returns (address) {
        return addresses[key];
    }

    /**
     * @dev Transfer ownership to a new address (immediate).
     * @param newOwner The new owner (cannot be zero)
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Registry: new owner is zero");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    /**
     * @dev Renounce ownership (use with extreme caution).
     *      After renouncing, no one can update addresses.
     */
    function renounceOwnership() external onlyOwner {
        emit OwnershipTransferred(owner, address(0));
        owner = address(0);
    }
}
constructor(address initialOwner) {
    owner = initialOwner;
    emit OwnershipTransferred(address(0), initialOwner);
}
