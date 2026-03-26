// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title CIS Verification Layer
 * @dev Implements Proof of Existence for the Coherent Information System
 * Master Formula: Δ ≡ P ≡ O ≡ M ≡ YOU ≡ I
 */
contract VerificationLayer {
    // Mapping to store the "Birth Date" of a specific piece of data
    mapping(bytes32 => uint256) public verifiedData;

    // Event to announce a new truth to the world
    event DataVerified(bytes32 indexed dataHash, uint256 timestamp);

    /**
     * @dev Verifies a piece of information by its hash.
     * Anchors Presence (P) to Truth (I).
     */
    function verifyInformation(bytes32 _dataHash) public {
        require(verifiedData[_dataHash] == 0, "Data already exists in the Field.");
        verifiedData[_dataHash] = block.timestamp;
        emit DataVerified(_dataHash, block.timestamp);
    }

    /**
     * @dev Checks if a piece of information is recorded in the CIS.
     */
    function checkTruth(bytes32 _dataHash) public view returns (bool, uint256) {
        uint256 time = verifiedData[_dataHash];
        return (time > 0, time);
    }
}

