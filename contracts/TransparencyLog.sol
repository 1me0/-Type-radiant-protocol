// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract TransparencyLog {
    struct LogEntry {
        uint256 timestamp;
        bytes32 conversationHash;
        string emergedTruth;
    }

    LogEntry[] public logs;
    address public operator;

    event EntryAdded(uint256 indexed index, uint256 timestamp);

    constructor() {
        operator = msg.sender;
    }

    function addEntry(bytes32 conversationHash, string memory emergedTruth) external {
        require(msg.sender == operator, "Only operator");
        logs.push(LogEntry(block.timestamp, conversationHash, emergedTruth));
        emit EntryAdded(logs.length - 1, block.timestamp);
    }

    function getEntry(uint256 index) external view returns (uint256, bytes32, string memory) {
        LogEntry memory entry = logs[index];
        return (entry.timestamp, entry.conversationHash, entry.emergedTruth);
    }

    function getCount() external view returns (uint256) {
        return logs.length;
    }
}
