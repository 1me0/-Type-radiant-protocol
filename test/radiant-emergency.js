const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("Radiant Protocol: Emergency & Governance", function () {
  let radiant, owner, council1, council2, user1;

  beforeEach(async function () {
    // 1. Get Signers
    [owner, council1, council2, user1] = await ethers.getSigners();

    // 2. Deploy Contract
    const Radiant = await ethers.getContractFactory("Radiant");
    radiant = await Radiant.deploy();
    // In Ethers v6, we use waitForDeployment()
    await radiant.waitForDeployment();

    // 3. Setup Council (Initial Architect setup)
    await radiant.setWorkerAddress(owner.address); // Setting owner as worker for testing
    
    // Manual setup for council logic (assuming your contract uses isCouncil mapping)
    // In a real scenario, these would be calls to your addCouncilMember function
    // For this test, we assume the Architect has added these two.
  });

  describe("Emergency Staking Vector", function () {
    it("should prevent staking when the emergency pause is active", async function () {
      // Logic: Council votes to pause
      await radiant.connect(council1).voteEmergencyAction("staking", true);
      await radiant.connect(council2).voteEmergencyAction("staking", true);

      expect(await radiant.stakingPaused()).to.equal(true);

      // Attempt to stake should fail
      await expect(
        user1.sendTransaction({
          to: await radiant.getAddress(),
          value: ethers.parseEther("1.0"),
        })
      ).to.be.revertedWith("Systemic Emergency: Staking is currently paused");
    });

    it("should require a majority (2/2) to execute an action", async function () {
      // Only one council member votes
      await radiant.connect(council1).voteEmergencyAction("staking", true);
      
      // The state should still be unpaused (false) because 1 < 2
      expect(await radiant.stakingPaused()).to.equal(false);
    });
  });

  describe("Emergency Proof Vector", function () {
    it("should block CIS score submissions during a proof emergency", async function () {
      await radiant.connect(council1).voteEmergencyAction("proofs", true);
      await radiant.connect(council2).voteEmergencyAction("proofs", true);

      const dummyHash = ethers.id("test message");
      const dummySig = "0x" + "00".repeat(65);

      await expect(
        radiant.connect(user1).submitCISScore(800, dummyHash, dummySig)
      ).to.be.revertedWith("Systemic Emergency: Proof submissions are currently paused");
    });
  });

  describe("Governance Integrity", function () {
    it("should only allow the Architect to change the worker address", async function () {
      await expect(
        radiant.connect(user1).setWorkerAddress(user1.address)
      ).to.be.revertedWith("Caller is not the Architect");
    });

    it("should allow the Architect to withdraw protocol funds", async function () {
      // Send some ETH to contract
      await user1.sendTransaction({
        to: await radiant.getAddress(),
        value: ethers.parseEther("5.0"),
      });

      const initialBalance = await ethers.provider.getBalance(owner.address);
      await radiant.connect(owner).withdraw();
      const finalBalance = await ethers.provider.getBalance(owner.address);

      expect(finalBalance).to.be.greaterThan(initialBalance);
    });
  });
});
        
