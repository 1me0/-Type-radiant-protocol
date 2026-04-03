const registry = new ethers.Contract(registryAddress, registryABI, provider);
const radiantShares = await registry.getAddress("RadiantShares");
