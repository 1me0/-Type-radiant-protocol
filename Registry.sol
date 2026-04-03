// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract Registry {
    address public owner;
    mapping(string => address) public addresses;

    event AddressSet(string key, address addr);

    constructor() {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    function setAddress(string calldata key, address addr) external onlyOwner {
        addresses[key] = addr;
        emit AddressSet(key, addr);
    }

    function getAddress(string calldata key) external view returns (address) {
        return addresses[key];
    }

    function transferOwnership(address newOwner) external onlyOwner {
        owner = newOwner;
    }
}
