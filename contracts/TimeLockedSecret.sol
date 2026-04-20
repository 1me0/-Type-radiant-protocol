// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title TimeLockedSecret
 * @notice Allows users to commit a secret hash and reveal it after a hold period or with architect approval.
 *         The architect can approve early; otherwise, the requester must wait HOLD_DURATION.
 *
 * Features:
 * - Users request access by providing the hash of a secret (e.g., a password or key).
 * - The secret can be revealed either after 5 days or immediately if the architect approves.
 * - The architect can also revoke an approval before revelation.
 * - Users can cancel unapproved requests.
 * - The architect can transfer their role to another address.
 */
contract TimeLockedSecret {
    address public architect;
    uint256 public constant HOLD_DURATION = 5 days;

    struct SecretRequest {
        bytes32 secretHash;      // keccak256(secret)
        uint256 requestTime;
        bool approved;
        bool revealed;
        address requester;       // address that made the request
    }

    mapping(bytes32 => SecretRequest) public requests;

    // Events
    event RequestCreated(bytes32 indexed requestId, address indexed requester, uint256 requestTime);
    event Approved(bytes32 indexed requestId, address indexed approver);
    event Revealed(bytes32 indexed requestId, address indexed revealer, string secret);
    event Cancelled(bytes32 indexed requestId, address indexed canceller);
    event ApprovalRevoked(bytes32 indexed requestId, address indexed revoker);
    event ArchitectTransferred(address indexed oldArchitect, address indexed newArchitect);
    event ArchitectRenounced(address indexed oldArchitect);

    modifier onlyArchitect() {
        require(msg.sender == architect, "TimeLockedSecret: not architect");
        _;
    }

    constructor() {
        architect = msg.sender;
    }

    /**
     * @dev Request access by providing the hash of the secret.
     * @param secretHash keccak256(secret)
     */
    function requestAccess(bytes32 secretHash) external {
        require(requests[secretHash].requestTime == 0, "TimeLockedSecret: already requested");
        requests[secretHash] = SecretRequest({
            secretHash: secretHash,
            requestTime: block.timestamp,
            approved: false,
            revealed: false,
            requester: msg.sender
        });
        emit RequestCreated(secretHash, msg.sender, block.timestamp);
    }

    /**
     * @dev Cancel an unapproved request (only the requester).
     * @param requestId The secretHash of the request.
     */
    function cancelRequest(bytes32 requestId) external {
        SecretRequest storage req = requests[requestId];
        require(req.requestTime != 0, "TimeLockedSecret: no such request");
        require(!req.approved, "TimeLockedSecret: cannot cancel approved request");
        require(req.requester == msg.sender, "TimeLockedSecret: not requester");
        delete requests[requestId];
        emit Cancelled(requestId, msg.sender);
    }

    /**
     * @dev Architect can approve a request early.
     * @param requestId The secretHash of the request.
     */
    function approve(bytes32 requestId) external onlyArchitect {
        SecretRequest storage req = requests[requestId];
        require(req.requestTime != 0, "TimeLockedSecret: no such request");
        require(!req.approved, "TimeLockedSecret: already approved");
        require(!req.revealed, "TimeLockedSecret: already revealed");
        req.approved = true;
        emit Approved(requestId, msg.sender);
    }

    /**
     * @dev Architect can revoke an approved request before it is revealed.
     * @param requestId The secretHash of the request.
     */
    function revokeApproval(bytes32 requestId) external onlyArchitect {
        SecretRequest storage req = requests[requestId];
        require(req.requestTime != 0, "TimeLockedSecret: no such request");
        require(req.approved, "TimeLockedSecret: not approved");
        require(!req.revealed, "TimeLockedSecret: already revealed");
        req.approved = false;
        emit ApprovalRevoked(requestId, msg.sender);
    }

    /**
     * @dev Reveal the secret after hold period or if approved.
     * @param requestId The secretHash of the request.
     * @param secret The actual secret string.
     */
    function reveal(bytes32 requestId, string calldata secret) external {
        SecretRequest storage req = requests[requestId];
        require(req.requestTime != 0, "TimeLockedSecret: no such request");
        require(!req.revealed, "TimeLockedSecret: already revealed");
        require(req.approved || block.timestamp >= req.requestTime + HOLD_DURATION, "TimeLockedSecret: hold period not passed");

        bytes32 hash = keccak256(abi.encodePacked(secret));
        require(hash == req.secretHash, "TimeLockedSecret: secret does not match");

        req.revealed = true;
        emit Revealed(requestId, msg.sender, secret);
        // Delete the request to save gas and prevent re‑revelation
        delete requests[requestId];
    }

    /**
     * @dev Check if a request is eligible for reveal.
     * @param requestId The secretHash.
     * @return true if approved or hold period passed and not yet revealed.
     */
    function canReveal(bytes32 requestId) external view returns (bool) {
        SecretRequest storage req = requests[requestId];
        if (req.requestTime == 0 || req.revealed) return false;
        return req.approved || block.timestamp >= req.requestTime + HOLD_DURATION;
    }

    /**
     * @dev Transfer the architect role to a new address (only current architect).
     * @param newArchitect The address of the new architect.
     */
    function transferArchitect(address newArchitect) external onlyArchitect {
        require(newArchitect != address(0), "TimeLockedSecret: invalid address");
        address old = architect;
        architect = newArchitect;
        emit ArchitectTransferred(old, newArchitect);
    }

    /**
     * @dev Renounce the architect role (sets architect to address(0)). Use with extreme caution.
     *      After renouncing, no one can approve or revoke approvals.
     */
    function renounceArchitect() external onlyArchitect {
        address old = architect;
        architect = address(0);
        emit ArchitectRenounced(old);
    }
}
