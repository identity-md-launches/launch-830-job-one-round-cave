#!/usr/bin/env python3
"""v4pool: read a Uniswap v4 pool's live state from a public Ethereum RPC.

Python 3 standard library only. Read-only: it makes eth_call requests and
nothing else. No keys, no wallets, no signing, no environment variables.

What it does:
  * keccak256 in pure Python (hashlib's sha3_256 is NOT Ethereum's keccak)
  * computes a v4 pool id from its PoolKey and checks it against an expected id
  * reads slot0 (sqrtPriceX96, tick, protocol fee, lp fee) and liquidity
    straight out of the PoolManager's storage with extsload(bytes32)
  * reads symbol / decimals / totalSupply of both tokens
  * turns it into human prices both ways, and decodes the hook permission bits

Default pool: ZTO / IMD (Zero To One, launch #737).
"""

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from decimal import Decimal, getcontext

getcontext().prec = 60

DEFAULT_RPC = "https://ethereum-rpc.publicnode.com"
POOL_MANAGER = "0x000000000004444c5dc75cB358380D2e3dE08A90"
POOLS_SLOT = 6          # StateLibrary.POOLS_SLOT
LIQUIDITY_OFFSET = 3    # StateLibrary.LIQUIDITY_OFFSET
DYNAMIC_FEE_FLAG = 0x800000

ZTO = "0xd782bdea4ef02a0bd391eb9089470c8080f0a68e"
IMD = "0xd34a99bc0f67ae1bbd63c660e6d0b0dd03e263b7"
ZTO_HOOKS = "0x784ff9a3ac5d88a30bfff6f7f2a270161fbe6000"
ZTO_POOL_ID = "0x888b07bd282f587d3c6b0fcb23e7fc55bbb33abe8910dd7492db815dc8dc5592"
ZTO_FEE = 12500
ZTO_TICK_SPACING = 60

# Hooks.sol permission flags live in the lowest 14 bits of the hook address.
HOOK_FLAGS = [
    (13, "beforeInitialize"), (12, "afterInitialize"),
    (11, "beforeAddLiquidity"), (10, "afterAddLiquidity"),
    (9, "beforeRemoveLiquidity"), (8, "afterRemoveLiquidity"),
    (7, "beforeSwap"), (6, "afterSwap"),
    (5, "beforeDonate"), (4, "afterDonate"),
    (3, "beforeSwapReturnDelta"), (2, "afterSwapReturnDelta"),
    (1, "afterAddLiquidityReturnDelta"), (0, "afterRemoveLiquidityReturnDelta"),
]

# ---------------------------------------------------------------- keccak256

_RC = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]
_ROT = [
    [0, 36, 3, 41, 18], [1, 44, 10, 45, 2], [62, 6, 43, 15, 61],
    [28, 55, 25, 21, 56], [27, 20, 39, 8, 14],
]
_M = (1 << 64) - 1


def _rol(v, n):
    return ((v << n) | (v >> (64 - n))) & _M if n else v


def _keccak_f(a):
    for rc in _RC:
        c = [a[x][0] ^ a[x][1] ^ a[x][2] ^ a[x][3] ^ a[x][4] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rol(c[(x + 1) % 5], 1) for x in range(5)]
        a = [[a[x][y] ^ d[x] for y in range(5)] for x in range(5)]
        b = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                b[y][(2 * x + 3 * y) % 5] = _rol(a[x][y], _ROT[x][y])
        a = [[b[x][y] ^ (~b[(x + 1) % 5][y] & b[(x + 2) % 5][y]) for y in range(5)]
             for x in range(5)]
        a[0][0] ^= rc
    return a


def _sponge(data: bytes, pad: int) -> bytes:
    rate = 136
    msg = bytearray(data)
    msg.append(pad)
    while len(msg) % rate:
        msg.append(0)
    msg[-1] |= 0x80
    a = [[0] * 5 for _ in range(5)]
    for off in range(0, len(msg), rate):
        block = msg[off:off + rate]
        for i in range(rate // 8):
            x, y = i % 5, i // 5
            a[x][y] ^= int.from_bytes(block[8 * i:8 * i + 8], "little")
        a = _keccak_f(a)
    out = b""
    for i in range(4):
        out += a[i % 5][i // 5].to_bytes(8, "little")
    return out


def keccak256(data: bytes) -> bytes:
    """Ethereum keccak256 (original Keccak padding 0x01, not SHA3's 0x06)."""
    return _sponge(data, 0x01)


def selector(signature: str) -> bytes:
    return keccak256(signature.encode())[:4]

# ---------------------------------------------------------------- ABI bits


def _addr(a: str) -> str:
    a = a.lower()
    if not (a.startswith("0x") and len(a) == 42):
        raise ValueError("not an address: %r" % a)
    int(a, 16)
    return a


def enc_uint(v: int) -> bytes:
    return (v % (1 << 256)).to_bytes(32, "big")


def enc_addr(a: str) -> bytes:
    return bytes.fromhex(_addr(a)[2:]).rjust(32, b"\0")


def signed(v: int, bits: int) -> int:
    v &= (1 << bits) - 1
    return v - (1 << bits) if v >> (bits - 1) else v


def sort_currencies(a: str, b: str):
    a, b = _addr(a), _addr(b)
    return (a, b) if int(a, 16) < int(b, 16) else (b, a)


def pool_id(currency0, currency1, fee, tick_spacing, hooks) -> str:
    """PoolIdLibrary.toId: keccak256(abi.encode(PoolKey))."""
    data = (enc_addr(currency0) + enc_addr(currency1) + enc_uint(fee)
            + enc_uint(tick_spacing) + enc_addr(hooks))
    return "0x" + keccak256(data).hex()


def pool_state_slot(pid: str) -> int:
    """StateLibrary._getPoolStateSlot: keccak256(abi.encodePacked(poolId, POOLS_SLOT))."""
    raw = bytes.fromhex(pid[2:]) + enc_uint(POOLS_SLOT)
    return int.from_bytes(keccak256(raw), "big")


def decode_slot0(word: int) -> dict:
    return {
        "sqrtPriceX96": word & ((1 << 160) - 1),
        "tick": signed(word >> 160, 24),
        "protocolFee": (word >> 184) & 0xFFFFFF,
        "lpFee": (word >> 208) & 0xFFFFFF,
    }


def split_protocol_fee(pf: int) -> dict:
    """ProtocolFeeLibrary: lower 12 bits zeroForOne, upper 12 bits oneForZero (pips)."""
    return {"zeroForOne": pf & 0xFFF, "oneForZero": (pf >> 12) & 0xFFF}


def decode_hook_flags(hooks: str) -> list:
    v = int(_addr(hooks), 16)
    return [name for bit, name in HOOK_FLAGS if v >> bit & 1]


def decode_string(hexdata: str) -> str:
    raw = bytes.fromhex(hexdata[2:])
    if len(raw) == 32:  # some old tokens return bytes32
        return raw.rstrip(b"\0").decode("utf-8", "replace")
    if len(raw) < 64:
        return ""
    off = int.from_bytes(raw[:32], "big")
    n = int.from_bytes(raw[off:off + 32], "big")
    return raw[off + 32:off + 32 + n].decode("utf-8", "replace")

# ---------------------------------------------------------------- RPC


class RPC:
    def __init__(self, url, timeout=20):
        self.url, self.timeout, self._id = url, timeout, 0

    def call(self, method, params):
        self._id += 1
        body = json.dumps({"jsonrpc": "2.0", "id": self._id,
                           "method": method, "params": params}).encode()
        req = urllib.request.Request(self.url, data=body, headers={
            "content-type": "application/json", "user-agent": "v4pool/1"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                resp = json.loads(r.read())
        except urllib.error.HTTPError as e:
            # public nodes answer some refusals (e.g. archive state) with HTTP 4xx + JSON
            try:
                resp = json.loads(e.read())
            except Exception:
                raise RuntimeError("%s: HTTP %d from %s" % (method, e.code, self.url))
        if "error" in resp:
            raise RuntimeError("%s: %s" % (method, resp["error"]))
        return resp["result"]

    def eth_call(self, to, data: bytes, block="latest") -> str:
        return self.call("eth_call", [{"to": to, "data": "0x" + data.hex()}, block])


def extsload(rpc, slot: int, block) -> int:
    out = rpc.eth_call(POOL_MANAGER, selector("extsload(bytes32)") + enc_uint(slot), block)
    return int(out, 16)


def token_info(rpc, token, block) -> dict:
    if int(token, 16) == 0:
        return {"address": token, "symbol": "ETH", "decimals": 18, "totalSupply": None}
    info = {"address": token}
    try:
        info["symbol"] = decode_string(rpc.eth_call(token, selector("symbol()"), block))
    except Exception:
        info["symbol"] = "?"
    info["decimals"] = int(rpc.eth_call(token, selector("decimals()"), block), 16)
    info["totalSupply"] = int(rpc.eth_call(token, selector("totalSupply()"), block), 16)
    return info

# ---------------------------------------------------------------- main logic


def price_from_sqrt(sqrt_price_x96: int, dec0: int, dec1: int) -> Decimal:
    """Human price of 1 token0 in token1."""
    p = (Decimal(sqrt_price_x96) / Decimal(2 ** 96)) ** 2
    return p * (Decimal(10) ** (dec0 - dec1))


def read_pool(rpc, token_a, token_b, fee, tick_spacing, hooks,
              expected_id=None, block="latest") -> dict:
    c0, c1 = sort_currencies(token_a, token_b)
    pid = pool_id(c0, c1, fee, tick_spacing, hooks)
    if expected_id and pid.lower() != expected_id.lower():
        raise SystemExit("pool id mismatch: computed %s, expected %s" % (pid, expected_id))
    if block == "latest":
        block = rpc.call("eth_blockNumber", [])
    base = pool_state_slot(pid)
    s0 = decode_slot0(extsload(rpc, base, block))
    liquidity = extsload(rpc, base + LIQUIDITY_OFFSET, block) & ((1 << 128) - 1)
    t0, t1 = token_info(rpc, c0, block), token_info(rpc, c1, block)
    out = {
        "block": int(block, 16),
        "poolManager": POOL_MANAGER,
        "poolId": pid,
        "poolIdVerified": bool(expected_id),
        "currency0": t0,
        "currency1": t1,
        "fee": fee,
        "dynamicFee": fee == DYNAMIC_FEE_FLAG,
        "tickSpacing": tick_spacing,
        "hooks": _addr(hooks),
        "hookPermissions": decode_hook_flags(hooks),
        "initialized": s0["sqrtPriceX96"] != 0,
        "slot0": s0,
        "protocolFeeSplit": split_protocol_fee(s0["protocolFee"]),
        "liquidity": liquidity,
    }
    if s0["sqrtPriceX96"]:
        p = price_from_sqrt(s0["sqrtPriceX96"], t0["decimals"], t1["decimals"])
        ptick = (Decimal("1.0001") ** s0["tick"]) * (Decimal(10) ** (t0["decimals"] - t1["decimals"]))
        out["price"] = {
            "%s_per_%s" % (t1["symbol"], t0["symbol"]): "%.12g" % p,
            "%s_per_%s" % (t0["symbol"], t1["symbol"]): "%.12g" % (1 / p),
            "fromTick_%s_per_%s" % (t1["symbol"], t0["symbol"]): "%.12g" % ptick,
        }
    return out


def selftest() -> int:
    checks = [
        ("keccak256('')", keccak256(b"").hex(),
         "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"),
        ("keccak256('abc')", keccak256(b"abc").hex(),
         "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45"),
        # same permutation with SHA3 padding must equal hashlib, across block edges
        ("permutation vs hashlib.sha3_256 (0..300 bytes)",
         str(all(_sponge(bytes(range(256))[:n] * 1 + b"x" * max(0, n - 256), 0x06)
                 == hashlib.sha3_256(bytes(range(256))[:n] + b"x" * max(0, n - 256)).digest()
                 for n in range(0, 301, 7))), "True"),
        ("selector transfer(address,uint256)", selector("transfer(address,uint256)").hex(), "a9059cbb"),
        ("selector balanceOf(address)", selector("balanceOf(address)").hex(), "70a08231"),
        ("ZTO/IMD pool id from PoolKey",
         pool_id(*sort_currencies(ZTO, IMD), ZTO_FEE, ZTO_TICK_SPACING, ZTO_HOOKS), ZTO_POOL_ID),
        ("protocol fee split 512125", str(split_protocol_fee(512125)),
         "{'zeroForOne': 125, 'oneForZero': 125}"),
        ("signed int24 -1", str(signed(0xFFFFFF, 24)), "-1"),
        ("hook flags 0x...6000", ",".join(decode_hook_flags(ZTO_HOOKS)), "beforeInitialize"),
    ]
    bad = 0
    for name, got, want in checks:
        ok = got == want
        bad += not ok
        print("%s  %s%s" % ("ok  " if ok else "FAIL", name, "" if ok else "  got %s want %s" % (got, want)))
    print("selftest: %d/%d passed" % (len(checks) - bad, len(checks)))
    return 1 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Read a Uniswap v4 pool's live state (default: ZTO/IMD).")
    ap.add_argument("--rpc", default=DEFAULT_RPC)
    ap.add_argument("--token-a", default=ZTO, help="either pool token (order does not matter); 0x000..0 for ETH")
    ap.add_argument("--token-b", default=IMD)
    ap.add_argument("--fee", type=int, default=ZTO_FEE, help="lp fee in hundredths of a bip; 8388608 = dynamic")
    ap.add_argument("--tick-spacing", type=int, default=ZTO_TICK_SPACING)
    ap.add_argument("--hooks", default=ZTO_HOOKS)
    ap.add_argument("--expect-id", default=None, help="fail unless the computed pool id equals this")
    ap.add_argument("--block", default="latest", help="block number (decimal) or 'latest'")
    ap.add_argument("--json", action="store_true", help="print raw JSON")
    ap.add_argument("--selftest", action="store_true", help="offline checks only, no network")
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()
    expect = a.expect_id
    if expect is None and a.token_a.lower() in (ZTO, IMD) and a.token_b.lower() in (ZTO, IMD) \
            and a.fee == ZTO_FEE and a.tick_spacing == ZTO_TICK_SPACING and a.hooks.lower() == ZTO_HOOKS:
        expect = ZTO_POOL_ID
    block = a.block if a.block == "latest" else hex(int(a.block))
    try:
        r = read_pool(RPC(a.rpc), a.token_a, a.token_b, a.fee, a.tick_spacing, a.hooks, expect, block)
    except (ValueError, RuntimeError, OSError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 1
    if a.json:
        print(json.dumps(r, indent=2, default=str))
        return 0
    t0, t1, s0 = r["currency0"], r["currency1"], r["slot0"]
    print("block        %d" % r["block"])
    print("pool id      %s%s" % (r["poolId"], "  (matches expected)" if r["poolIdVerified"] else ""))
    print("currency0    %s %s (decimals %d)" % (t0["symbol"], t0["address"], t0["decimals"]))
    print("currency1    %s %s (decimals %d)" % (t1["symbol"], t1["address"], t1["decimals"]))
    print("fee          %d (%s)  tickSpacing %d" % (r["fee"], "dynamic" if r["dynamicFee"]
                                                   else "%.4f%%" % (r["fee"] / 10000), r["tickSpacing"]))
    print("hooks        %s  [%s]" % (r["hooks"], ", ".join(r["hookPermissions"]) or "none"))
    if not r["initialized"]:
        print("state        NOT INITIALIZED (no pool with this key)")
        return 2
    print("sqrtPriceX96 %d" % s0["sqrtPriceX96"])
    pf = r["protocolFeeSplit"]
    print("tick         %d   lpFee %d   protocolFee %d/%d pips (0->1 / 1->0)"
          % (s0["tick"], s0["lpFee"], pf["zeroForOne"], pf["oneForZero"]))
    print("liquidity    %d" % r["liquidity"])
    for k, v in r["price"].items():
        print("price        %s = %s" % (k, v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
