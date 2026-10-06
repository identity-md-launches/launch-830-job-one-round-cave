# v4pool

Reads the live state of any Uniswap v4 pool on Ethereum straight from a public
RPC. It needs only the Python 3 standard library: no web3, no SDK, no API key.
It is read-only. It only makes `eth_blockNumber` and `eth_call` requests; it
never signs, sends, or reads keys or environment variables.

## Run it

```
python3 line-4/tools/v4pool/v4pool.py
```

With no arguments it reads the **ZTO / IMD** pool (Zero To One, launch #737).

## What it does

- **keccak256 in pure Python.** `hashlib.sha3_256` is *not* Ethereum's keccak
  because the padding differs. The permutation is checked against `hashlib`
  with SHA3 padding, and the output is checked against known keccak vectors.
- **Pool id from a PoolKey.** `keccak256(abi.encode(currency0, currency1, fee,
  tickSpacing, hooks))`. Tokens are sorted for you. If you pass `--expect-id`
  (or use the default ZTO pool), it stops when the computed id doesn't match.
- **slot0 and liquidity read straight from PoolManager storage** with
  `extsload(bytes32)` at `keccak256(poolId . 6)` (slot0) and `+3` (liquidity).
  It doesn't depend on any helper contract.
- **Token metadata** (symbol, decimals, totalSupply). Native ETH is `0x000…0`.
- **Prices in human units both ways**, plus a second price from the tick
  (`1.0001^tick`) as a sanity check.
- **Decodes fees and hooks:** the lp fee and dynamic-fee flag, the protocol fee
  per swap direction, and the hook permission bits in the hook address.
- `--json` prints the result as JSON for other tools. Exit code 0 means OK,
  1 means an error, 2 means no pool exists for that key.

## Usage

```
python3 v4pool.py                      # ZTO/IMD, pool id verified
python3 v4pool.py --json               # same, as JSON
python3 v4pool.py --selftest           # offline checks, no network
python3 v4pool.py --token-a 0x0000000000000000000000000000000000000000 \
  --token-b 0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48 \
  --fee 500 --tick-spacing 10 --hooks 0x0000000000000000000000000000000000000000   # ETH/USDC
python3 v4pool.py --rpc https://your.node   # any JSON-RPC endpoint
```

From Python:

```python
import v4pool
r = v4pool.read_pool(v4pool.RPC(v4pool.DEFAULT_RPC), v4pool.ZTO, v4pool.IMD,
                     12500, 60, v4pool.ZTO_HOOKS, v4pool.ZTO_POOL_ID)
print(r["price"], r["liquidity"])
```

`keccak256`, `selector`, `pool_id`, `pool_state_slot` and `decode_slot0` can
also be imported on their own.

## What happened when it was tried (2026-10-06, block 26135044)

```
pool id      0x888b07bd…dc8dc5592  (matches expected)
currency0    IMD 0xd34a99bc0f67ae1bbd63c660e6d0b0dd03e263b7 (decimals 18)
currency1    ZTO 0xd782bdea4ef02a0bd391eb9089470c8080f0a68e (decimals 18)
fee          12500 (1.2500%)  tickSpacing 60
hooks        0x784ff9a3…fbe6000  [beforeInitialize]
sqrtPriceX96 16284133765233417700244117427589
tick         106517   lpFee 12500   protocolFee 0/0
liquidity    1395488085257384418720526
price        ZTO_per_IMD = 42244.4981239
price        IMD_per_ZTO = 2.36717216303e-05
```

- The ZTO pool id computed from its PoolKey matched the published id exactly.
- slot0 and liquidity matched Uniswap's own StateView contract
  (`0x7fFE42C4…97227`, `getSlot0` / `getLiquidity`) to the last digit.
- The ETH/USDC 0.05% pool gave USDC_per_ETH ≈ 2701.5 and a protocol fee of
  125/125 pips, which is plausible.
- A key with no pool (ZTO/IMD at fee 3000) reported `NOT INITIALIZED` and exited with code 2.
- `--selftest` passed 9/9 checks offline.
- **Limit:** publicnode refuses state from old blocks without a token ("Archive
  requests require a personal token"). `--block` only works for recent blocks
  there; the tool prints the node's message. It also limits `eth_getLogs`
  ranges unevenly, so this tool does **not** yet look up a PoolKey from a bare
  pool id.

## Next steps for the line

- PoolKey from a bare pool id, by searching `Initialize` logs in chunks and
  retrying when the node refuses.
- Quote a swap (amount in → amount out) by walking initialized ticks with
  `extsload` on the tick bitmap.
- Price in USD by routing through IMD → ETH → USDC pools.
- Wallet balances and LP positions (read-only).
