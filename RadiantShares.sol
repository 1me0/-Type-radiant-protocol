// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";

/**
 * @title RadiantShares
 * @dev ERC20 token with:
 *      - Max supply (100M)
 *      - 50/50 mint split (architect / treasury)
 *      - Configurable transfer tax (≤5%) to architect (perpetual income)
 *      - Tax exempt for architect and treasury wallets
 *      - Timelocked mint proposals (2 days)
 *      - Timelocked address changes (2 days)
 *      - Pausable (emergency stop)
 *      - Admin role cannot be renounced
 */
contract RadiantShares is ERC20, AccessControl, ReentrancyGuard, Pausable {
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant GOVERNOR_ROLE = keccak256("GOVERNOR_ROLE");

    // ==================== Supply Cap ====================
    uint256 public constant MAX_SUPPLY = 100_000_000 * 10**18; // 100 million tokens

    // ==================== Mint Split ====================
    address public architectWallet;
    address public protocolTreasury;

    // ==================== Transfer Tax (Perpetual Income) ====================
    uint256 public transferTaxBasisPoints; // default 100 = 1%
    uint256 public constant MAX_TRANSFER_TAX = 500; // 5% max

    // ==================== Timelock for Minting ====================
    struct MintProposal {
        uint256 amount;
        address recipientTreasury;
        address recipientArchitect;
        uint256 proposedAt;
        bool executed;
    }
    mapping(bytes32 => MintProposal) public mintProposals;
    uint256 public constant MINT_TIMELOCK_DELAY = 2 days;

    // ==================== Timelock for Address Changes ====================
    struct PendingUpdate {
        address pendingValue;
        uint256 pendingTimestamp;
    }
    mapping(bytes32 => PendingUpdate) public pendingUpdates;
    uint256 public constant ADDRESS_TIMELOCK_DELAY = 2 days;

    // ==================== Events ====================
    event ArchitectWalletProposed(address indexed newWallet, uint256 timestamp);
    event ArchitectWalletExecuted(address indexed newWallet);
    event ProtocolTreasuryProposed(address indexed newTreasury, uint256 timestamp);
    event ProtocolTreasuryExecuted(address indexed newTreasury);
    event TransferTaxUpdated(uint256 newTaxBasisPoints);
    event MintProposed(bytes32 indexed id, address indexed treasuryRecipient, address indexed architectRecipient, uint256 amount, uint256 timestamp);
    event MintExecuted(bytes32 indexed id, uint256 architectShare, uint256 treasuryShare);
    event MintTimelockCancelled(bytes32 indexed id);
    event MintWithReceiver(address indexed minter, address indexed receiver, uint256 amount);
    event EmergencyMint(address indexed governor, address indexed recipient, uint256 amount);

    /**
     * @dev Constructor sets initial wallets, tax, and roles.
     */
    constructor(
        string memory name,
        string memory symbol,
        address _architectWallet,
        address _protocolTreasury
    ) ERC20(name, symbol) {
        require(_architectWallet != address(0), "Invalid architect wallet");
        require(_protocolTreasury != address(0), "Invalid protocol treasury");
        architectWallet = _architectWallet;
        protocolTreasury = _protocolTreasury;
        transferTaxBasisPoints = 100; // 1% default

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(GOVERNOR_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
    }

    // ==================== Modifiers ====================
    modifier onlyGovernor() {
        require(hasRole(GOVERNOR_ROLE, msg.sender), "Caller is not governor");
        _;
    }

    modifier onlyMinter() {
        require(hasRole(MINTER_ROLE, msg.sender), "Caller is not minter");
        _;
    }

    // ==================== Override _mint to enforce max supply ====================
    function _mint(address account, uint256 amount) internal virtual override {
        require(totalSupply() + amount <= MAX_SUPPLY, "Exceeds max supply");
        super._mint(account, amount);
    }

    // ==================== Transfer Tax (overrides _transfer) ====================
    function _transfer(address from, address to, uint256 amount) internal virtual override whenNotPaused {
        uint256 tax = 0;
        // Tax applies ONLY to user-to-user transfers.
        // architectWallet and protocolTreasury are EXEMPT (no tax when they send or receive).
        if (transferTaxBasisPoints > 0 && from != architectWallet && from != protocolTreasury && to != architectWallet && to != protocolTreasury) {
            tax = (amount * transferTaxBasisPoints) / 10000;
            if (tax > 0) {
                super._transfer(from, architectWallet, tax);
            }
        }
        uint256 amountAfterTax = amount - tax;
        super._transfer(from, to, amountAfterTax);
    }

    // ==================== Pausable ====================
    function pause() external onlyGovernor {
        _pause();
        emit Paused(msg.sender);
    }

    function unpause() external onlyGovernor {
        _unpause();
        emit Unpaused(msg.sender);
    }

    // ==================== Transfer Tax Management ====================
    function setTransferTax(uint256 _taxBasisPoints) external onlyGovernor {
        require(_taxBasisPoints <= MAX_TRANSFER_TAX, "Tax exceeds max");
        transferTaxBasisPoints = _taxBasisPoints;
        emit TransferTaxUpdated(_taxBasisPoints);
    }

    // ==================== Mint Split Functions ====================
    /**
     * @dev Direct mint with 50/50 split (no timelock – for immediate needs, but respects max supply)
     */
    function mint(uint256 amount) external onlyMinter nonReentrant whenNotPaused {
        require(amount > 0, "Amount must be positive");
        require(totalSupply() + amount <= MAX_SUPPLY, "Exceeds max supply");

        uint256 half = amount / 2;
        uint256 architectShare = half;
        uint256 treasuryShare = amount - half; // odd amounts favour treasury

        if (architectShare > 0) _mint(architectWallet, architectShare);
        if (treasuryShare > 0) _mint(protocolTreasury, treasuryShare);
    }

    /**
     * @dev Mint with custom receiver (no split – for rewards, etc.)
     */
    function mintWithReceiver(uint256 amount, address receiver) external onlyMinter nonReentrant whenNotPaused {
        require(amount > 0, "Amount must be positive");
        require(receiver != address(0), "Invalid receiver");
        require(totalSupply() + amount <= MAX_SUPPLY, "Exceeds max supply");
        _mint(receiver, amount);
        emit MintWithReceiver(msg.sender, receiver, amount);
    }

    // ==================== Timelocked Minting (for large or scheduled mints) ====================
    function proposeMint(uint256 amount) external onlyMinter {
        require(amount > 0, "Amount must be positive");
        require(totalSupply() + amount <= MAX_SUPPLY, "Exceeds max supply");

        bytes32 id = keccak256(abi.encodePacked(block.timestamp, msg.sender, amount));
        mintProposals[id] = MintProposal({
            amount: amount,
            recipientTreasury: protocolTreasury,
            recipientArchitect: architectWallet,
            proposedAt: block.timestamp,
            executed: false
        });
        emit MintProposed(id, protocolTreasury, architectWallet, amount, block.timestamp);
    }

    function executeMint(bytes32 id) external onlyMinter nonReentrant whenNotPaused {
        MintProposal storage proposal = mintProposals[id];
        require(!proposal.executed, "Already executed");
        require(block.timestamp >= proposal.proposedAt + MINT_TIMELOCK_DELAY, "Timelock not expired");
        require(totalSupply() + proposal.amount <= MAX_SUPPLY, "Exceeds max supply");

        proposal.executed = true;

        uint256 half = proposal.amount / 2;
        uint256 architectShare = half;
        uint256 treasuryShare = proposal.amount - half;

        if (architectShare > 0) _mint(proposal.recipientArchitect, architectShare);
        if (treasuryShare > 0) _mint(proposal.recipientTreasury, treasuryShare);

        emit MintExecuted(id, architectShare, treasuryShare);
    }

    function cancelMintProposal(bytes32 id) external onlyMinter {
        MintProposal storage proposal = mintProposals[id];
        require(!proposal.executed, "Already executed");
        delete mintProposals[id];
        emit MintTimelockCancelled(id);
    }

    // ==================== Emergency Mint (Governor only, respects max supply) ====================
    function emergencyMint(address recipient, uint256 amount) external onlyGovernor whenNotPaused {
        require(amount > 0, "Amount zero");
        require(recipient != address(0), "Invalid recipient");
        require(totalSupply() + amount <= MAX_SUPPLY, "Exceeds max supply");
        _mint(recipient, amount);
        emit EmergencyMint(msg.sender, recipient, amount);
    }

    // ==================== Timelock for Address Changes ====================
    function proposeArchitectWallet(address newWallet) external onlyGovernor {
        require(newWallet != address(0), "Invalid address");
        bytes32 id = keccak256(abi.encodePacked("architectWallet"));
        pendingUpdates[id] = PendingUpdate(newWallet, block.timestamp);
        emit ArchitectWalletProposed(newWallet, block.timestamp);
    }

    function executeArchitectWallet() external onlyGovernor {
        bytes32 id = keccak256(abi.encodePacked("architectWallet"));
        PendingUpdate memory pending = pendingUpdates[id];
        require(pending.pendingValue != address(0), "No pending update");
        require(block.timestamp >= pending.pendingTimestamp + ADDRESS_TIMELOCK_DELAY, "Timelock not expired");
        architectWallet = pending.pendingValue;
        delete pendingUpdates[id];
        emit ArchitectWalletExecuted(architectWallet);
    }

    function proposeProtocolTreasury(address newTreasury) external onlyGovernor {
        require(newTreasury != address(0), "Invalid address");
        bytes32 id = keccak256(abi.encodePacked("protocolTreasury"));
        pendingUpdates[id] = PendingUpdate(newTreasury, block.timestamp);
        emit ProtocolTreasuryProposed(newTreasury, block.timestamp);
    }

    function executeProtocolTreasury() external onlyGovernor {
        bytes32 id = keccak256(abi.encodePacked("protocolTreasury"));
        PendingUpdate memory pending = pendingUpdates[id];
        require(pending.pendingValue != address(0), "No pending update");
        require(block.timestamp >= pending.pendingTimestamp + ADDRESS_TIMELOCK_DELAY, "Timelock not expired");
        protocolTreasury = pending.pendingValue;
        delete pendingUpdates[id];
        emit ProtocolTreasuryExecuted(protocolTreasury);
    }

    // ==================== Prevent Renounce of Admin Role ====================
    /**
     * @dev Override renounceRole to prevent renouncing the DEFAULT_ADMIN_ROLE.
     * Governance must always retain at least one admin.
     */
    function renounceRole(bytes32 role, address account) public virtual override {
        require(role != DEFAULT_ADMIN_ROLE, "Cannot renounce admin role");
        super.renounceRole(role, account);
    }
}
