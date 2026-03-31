// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract TimeLockedSecret {
    address public architect;
    uint256 public constant HOLD_DURATION = 5 days;

    struct SecretRequest {
        bytes32 secretHash;      // keccak256(secret)
        uint256 requestTime;
        bool approved;
        bool revealed;
    }

    mapping(bytes32 => SecretRequest) public requests;

    event RequestCreated(bytes32 indexed requestId, uint256 requestTime);
    event Approved(bytes32 indexed requestId);
    event Revealed(bytes32 indexed requestId, string secret);

    modifier onlyArchitect() {
        require(msg.sender == architect, "Not architect");
        _;
    }

    constructor() {
        architect = msg.sender;
    }

    // Request access by providing the hash of the secret
    function requestAccess(bytes32 secretHash) external {
        require(requests[secretHash].requestTime == 0, "Already requested");
        requests[secretHash] = SecretRequest({
            secretHash: secretHash,
            requestTime: block.timestamp,
            approved: false,
            revealed: false
        });
        emit RequestCreated(secretHash, block.timestamp);
    }

    // Architect can approve early
    function approve(bytes32 requestId) external onlyArchitect {
        SecretRequest storage req = requests[requestId];
        require(req.requestTime != 0, "No such request");
        require(!req.approved, "Already approved");
        req.approved = true;
        emit Approved(requestId);
    }

    // After hold period or approval, reveal the actual secret
    function reveal(bytes32 requestId, string calldata secret) external {
        SecretRequest storage req = requests[requestId];
        require(req.requestTime != 0, "No such request");
        require(!req.revealed, "Already revealed");
        require(req.approved || block.timestamp >= req.requestTime + HOLD_DURATION, "Hold period not passed");

        bytes32 hash = keccak256(abi.encodePacked(secret));
        require(hash == req.secretHash, "Secret does not match");

        req.revealed = true;
        emit Revealed(requestId, secret);
    }
}
