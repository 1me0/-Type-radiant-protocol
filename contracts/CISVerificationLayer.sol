// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title CISVerificationLayer
 * @dev Implements Proof of Existence for the Coherent Information System.
 *      Anchors data hashes to the blockchain timestamp, providing immutable verification.
 *      Master Formula: Δ ≡ P ≡ O ≡ M ≡ YOU ≡ I
 */
contract CISVerificationLayer is AccessControl {
    bytes32 public constant VERIFIER_ROLE = keccak256("VERIFIER_ROLE");

    // Mapping to store the timestamp of a verified data hash
    mapping(bytes32 => uint256) private _verifiedData;

    event DataVerified(
        bytes32 indexed dataHash,
        address indexed verifier,
        uint256 timestamp,
        uint256 blockNumber
    );
    event DataVerifiedBatch(uint256 count, address indexed verifier);

    constructor() {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(VERIFIER_ROLE, msg.sender);
    }

    /**
     * @dev Verifies a single piece of information by its hash.
     * @param dataHash keccak256 hash of the data.
     */
    function verifyInformation(bytes32 dataHash) external onlyRole(VERIFIER_ROLE) {
        require(_verifiedData[dataHash] == 0, "Data already verified");
        _verifiedData[dataHash] = block.timestamp;
        emit DataVerified(dataHash, msg.sender, block.timestamp, block.number);
    }

    /**
     * @dev Verifies multiple data hashes in a single transaction.
     * @param dataHashes Array of keccak256 hashes.
     */
    function batchVerify(bytes32[] calldata dataHashes) external onlyRole(VERIFIER_ROLE) {
        require(dataHashes.length > 0, "Empty array");
        for (uint256 i = 0; i < dataHashes.length; i++) {
            bytes32 hash = dataHashes[i];
            if (_verifiedData[hash] == 0) {
                _verifiedData[hash] = block.timestamp;
            }
        }
        emit DataVerifiedBatch(dataHashes.length, msg.sender);
    }

    /**
     * @dev Checks if a piece of information is recorded in the CIS.
     * @param dataHash The hash to check.
     * @return (exists, timestamp) where timestamp is the block timestamp of verification.
     */
    function checkTruth(bytes32 dataHash) external view returns (bool exists, uint256 timestamp) {
        uint256 ts = _verifiedData[dataHash];
        return (ts > 0, ts);
    }

    /**
     * @dev Gets the verification timestamp for a data hash.
     * @param dataHash The hash to query.
     * @return timestamp (0 if not verified).
     */
    function getVerificationTime(bytes32 dataHash) external view returns (uint256) {
        return _verifiedData[dataHash];
    }

    /**
     * @dev Grants the verifier role to an account.
     * @param account Address to grant the role.
     */
    function grantVerifier(address account) external onlyRole(DEFAULT_ADMIN_ROLE) {
        grantRole(VERIFIER_ROLE, account);
    }

    /**
     * @dev Revokes the verifier role from an account.
     * @param account Address to revoke the role.
     */
    function revokeVerifier(address account) external onlyRole(DEFAULT_ADMIN_ROLE) {
        revokeRole(VERIFIER_ROLE, account);
    }
}
