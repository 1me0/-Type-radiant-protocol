// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/AccessControl.sol";

/**
 * @title TransparencyLog
 * @notice Stores an immutable, auditable log of emerged truths with pagination.
 *         Only accounts with OPERATOR_ROLE can add entries.
 *
 * Features:
 * - Append‑only log of truths.
 * - Configurable maximum number of entries (can be increased or locked).
 * - Pagination support for efficient querying.
 * - Role‑based access control.
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

    // Events
    event EntryAdded(uint256 indexed index, uint256 timestamp, bytes32 conversationHash);
    event MaxEntriesUpdated(uint256 newMax, uint256 oldMax);
    event MaxEntriesLocked();

    constructor(uint256 _maxEntries) {
        require(_maxEntries >= 1, "TransparencyLog: maxEntries must be at least 1");
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(OPERATOR_ROLE, msg.sender);
        maxEntries = _maxEntries;
        isMaxEntriesLocked = false;
    }

    /**
     * @notice Add a new log entry (only OPERATOR_ROLE).
     * @param conversationHash Hash of the conversation (e.g., keccak256 of participants).
     * @param emergedTruth The emerged truth statement (stored as string).
     */
    function addEntry(bytes32 conversationHash, string memory emergedTruth) external onlyRole(OPERATOR_ROLE) {
        require(bytes(emergedTruth).length > 0, "TransparencyLog: empty truth");
        require(_logs.length < maxEntries, "TransparencyLog: log limit reached");
        uint256 index = _logs.length;
        _logs.push(LogEntry(block.timestamp, conversationHash, emergedTruth));
        emit EntryAdded(index, block.timestamp, conversationHash);
    }

    /**
     * @notice Get a single entry by index.
     * @param index The entry index (0‑based).
     * @return timestamp Block timestamp when the entry was added.
     * @return conversationHash Hash of the conversation.
     * @return emergedTruth The truth statement.
     */
    function getEntry(uint256 index) external view returns (uint256 timestamp, bytes32 conversationHash, string memory emergedTruth) {
        require(index < _logs.length, "TransparencyLog: index out of bounds");
        LogEntry memory entry = _logs[index];
        return (entry.timestamp, entry.conversationHash, entry.emergedTruth);
    }

    /**
     * @notice Get a paginated list of entries.
     * @param start Starting index (inclusive).
     * @param count Maximum number of entries to return.
     * @return An array of LogEntry structs.
     */
    function getEntries(uint256 start, uint256 count) external view returns (LogEntry[] memory) {
        require(start < _logs.length, "TransparencyLog: start out of bounds");
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
     * @notice Get the most recent N entries (from the end).
     * @param n Number of entries to retrieve (max `n`).
     * @return An array of the latest LogEntry structs (most recent last).
     */
    function getLatestEntries(uint256 n) external view returns (LogEntry[] memory) {
        uint256 total = _logs.length;
        if (n > total) n = total;
        if (n == 0) return new LogEntry[](0);
        LogEntry[] memory result = new LogEntry[](n);
        for (uint256 i = 0; i < n; i++) {
            result[i] = _logs[total - n + i];
        }
        return result;
    }

    /**
     * @notice Get total number of entries.
     * @return The total count.
     */
    function getCount() external view returns (uint256) {
        return _logs.length;
    }

    /**
     * @notice Update the maximum number of entries (only DEFAULT_ADMIN_ROLE).
     * @param newMax New maximum (must be at least 1 and >= current count).
     */
    function setMaxEntries(uint256 newMax) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(!isMaxEntriesLocked, "TransparencyLog: max entries locked");
        require(newMax >= _logs.length, "TransparencyLog: cannot be less than current count");
        require(newMax >= 1, "TransparencyLog: maxEntries must be at least 1");
        uint256 oldMax = maxEntries;
        maxEntries = newMax;
        emit MaxEntriesUpdated(newMax, oldMax);
    }

    /**
     * @notice Permanently lock the maximum entries limit (only DEFAULT_ADMIN_ROLE).
     */
    function lockMaxEntries() external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(!isMaxEntriesLocked, "TransparencyLog: already locked");
        isMaxEntriesLocked = true;
        emit MaxEntriesLocked();
    }

    /**
     * @notice Grant operator role (only DEFAULT_ADMIN_ROLE).
     * @param account Address to grant the role.
     */
    function grantOperator(address account) external onlyRole(DEFAULT_ADMIN_ROLE) {
        grantRole(OPERATOR_ROLE, account);
    }

    /**
     * @notice Revoke operator role (only DEFAULT_ADMIN_ROLE).
     * @param account Address to revoke the role.
     */
    function revokeOperator(address account) external onlyRole(DEFAULT_ADMIN_ROLE) {
        revokeRole(OPERATOR_ROLE, account);
    }
}
