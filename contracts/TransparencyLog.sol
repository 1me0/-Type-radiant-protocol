// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title TransparencyLog
 * @notice Stores an immutable, auditable log of emerged truths with pagination.
 *         Only accounts with OPERATOR_ROLE can add entries.
 */
contract TransparencyLog is AccessControl {
    bytes32 public constant OPERATOR_ROLE = keccak256("OPERATOR_ROLE");

    struct LogEntry {
        uint256 timestamp;
        bytes32 conversationHash;
        string emergedTruth;
    }

    LogEntry[] private _logs;
    uint256 public maxEntries;
    bool public isMaxEntriesLocked;

    event EntryAdded(uint256 indexed index, uint256 timestamp, bytes32 conversationHash);
    event MaxEntriesUpdated(uint256 newMax, uint256 oldMax);
    event MaxEntriesLocked();

    constructor(uint256 _maxEntries) {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(OPERATOR_ROLE, msg.sender);
        maxEntries = _maxEntries;
        isMaxEntriesLocked = false;
    }

    /**
     * @notice Add a new log entry (only OPERATOR_ROLE).
     * @param conversationHash Hash of the conversation (e.g., keccak256 of participants).
     * @param emergedTruth The emerged truth statement.
     */
    function addEntry(bytes32 conversationHash, string memory emergedTruth) external onlyRole(OPERATOR_ROLE) {
        require(bytes(emergedTruth).length > 0, "Empty truth");
        require(_logs.length < maxEntries, "Log limit reached");
        uint256 index = _logs.length;
        _logs.push(LogEntry(block.timestamp, conversationHash, emergedTruth));
        emit EntryAdded(index, block.timestamp, conversationHash);
    }

    /**
     * @notice Get a single entry by index.
     * @param index The entry index.
     */
    function getEntry(uint256 index) external view returns (uint256 timestamp, bytes32 conversationHash, string memory emergedTruth) {
        require(index < _logs.length, "Index out of bounds");
        LogEntry memory entry = _logs[index];
        return (entry.timestamp, entry.conversationHash, entry.emergedTruth);
    }

    /**
     * @notice Get multiple entries with pagination.
     * @param start Starting index (inclusive).
     * @param count Maximum number of entries to return.
     * @return An array of entries.
     */
    function getEntries(uint256 start, uint256 count) external view returns (LogEntry[] memory) {
        require(start < _logs.length, "Start out of bounds");
        uint256 end = start + count;
        if (end > _logs.length) end = _logs.length;
        uint256 resultCount = end - start;
        LogEntry[] memory result = new LogEntry[](resultCount);
        for (uint256 i = 0; i < resultCount; i++) {
            result[i] = _logs[start + i];
        }
        return result;
    }

    /**
     * @notice Get total number of entries.
     */
    function getCount() external view returns (uint256) {
        return _logs.length;
    }

    /**
     * @notice Update the maximum number of entries (only DEFAULT_ADMIN_ROLE).
     * @param newMax New maximum (must be >= current count).
     */
    function setMaxEntries(uint256 newMax) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(!isMaxEntriesLocked, "Max entries locked");
        require(newMax >= _logs.length, "Cannot be less than current count");
        uint256 oldMax = maxEntries;
        maxEntries = newMax;
        emit MaxEntriesUpdated(newMax, oldMax);
    }

    /**
     * @notice Permanently lock the maximum entries limit (only DEFAULT_ADMIN_ROLE).
     */
    function lockMaxEntries() external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(!isMaxEntriesLocked, "Already locked");
        isMaxEntriesLocked = true;
        emit MaxEntriesLocked();
    }

    /**
     * @notice Grant operator role (only DEFAULT_ADMIN_ROLE).
     */
    function grantOperator(address account) external onlyRole(DEFAULT_ADMIN_ROLE) {
        grantRole(OPERATOR_ROLE, account);
    }

    /**
     * @notice Revoke operator role (only DEFAULT_ADMIN_ROLE).
     */
    function revokeOperator(address account) external onlyRole(DEFAULT_ADMIN_ROLE) {
        revokeRole(OPERATOR_ROLE, account);
    }
}
