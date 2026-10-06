# Used by line 4

## Pepe 01 (v4pool)
- Python 3 standard library: `urllib`, `json`, `hashlib` (only to check the keccak permutation), `decimal`, `argparse`.
- Public RPC: https://ethereum-rpc.publicnode.com (`eth_blockNumber`, `eth_call`; `eth_getLogs` only while exploring).
- Uniswap v4 PoolManager `0x000000000004444c5dc75cB358380D2e3dE08A90`: `extsload(bytes32)`; storage layout from v4-core `StateLibrary` (POOLS_SLOT = 6, LIQUIDITY_OFFSET = 3), `PoolIdLibrary`, `Hooks` flag bits, `ProtocolFeeLibrary`.
- Uniswap v4 StateView `0x7fFE42C4a5DEeA5b0feC41C94C136Cf115597227`: used once to cross-check results; the tool doesn't depend on it.
- ZTO `0xd782bdea4ef02a0bd391eb9089470c8080f0a68e`, IMD `0xd34a99bc0f67ae1bbd63c660e6d0b0dd03e263b7`, ZTO/IMD pool id `0x888b07bd…dc8dc5592`.
- The image tool provided to this assignment (an image-editing model) painted the wall mark on the given cave image.
