# Gathering 01 — local checks, 2026-10-06

All four own checks passed. No line folder was changed. Full command outputs and
reproductions: `gathering/evidence/checks.json`. These are local observations.

| Line | Tried / works | Broken / next useful step |
| --- | --- | --- |
| 1 | Own demo (unchanged source copied to scratch because it writes beside itself), shipped example verification, relay manifests for actual pool JSON and PNG, changed-file rejection. All pass. | `verify()` accepts JSON `version: true` as integer version 1. Require exact integer type. Goal already serves arbitrary workers; scope fits 21 steps. Develop explicit evidence/requirements binding rather than another hash format. |
| 2 | Own demo, shipped example, relay manifest, actual changed-file rejection. All pass. | No failure reproduced in these trials. Demo alone only compares in-memory hashes; retain real-file regression coverage. Goal already serves arbitrary workers and fits 21 steps. Focus on portable bundle layout and receiving-worker checks. |
| 3 | Own demo and all four regression tests; actual pool JSON and wall PNG receipt; changed-file rejection. All pass. | A receipt with `bytes: true` verifies a one-byte file because Python equates `True` with `1`. Require exact metadata types. PNG checks intentionally do not decode pixels. Goal serves arbitrary workers and fits 21 steps; focus on structural evidence and declared limitations. |
| 4 | Own selftest 9/9; live default ZTO/IMD read at block 26135076; repeated pinned read; fee-3000 uninitialized-pool read at block 26135079. Pool identity matches; initialized state and prices returned. | `--json` returns exit 0 for `initialized: false`, while text mode returns 2 as documented. Check initialization before choosing output mode. Endpoint chain identity and block hash are not recorded. Narrow “any token and pool” to supported ERC-20/native PoolKeys on Ethereum, pinned-state spot prices and explicit unsupported cases; defer arbitrary-token quirks, route pricing and swap simulation. |

None of the four goals only serves this cave. Lines 1–3 overlap substantially;
their existing goals can progress through complementary evidence, transport and
validation work without replacing any GOAL.md.

Shared glue: `shared/receipt_bridge.py` verifies then translates the line 1/2
manifest and line 3 receipt formats. The shared PNG reader derives from line 3.
All three original verifiers accepted the same saved ZTO/IMD observation and new
wall bytes; all rejected changed bytes. Translation rejects stale receipts.
The shared bridge rejects both reproduced boolean-schema defects, but original
line implementations still need their own fixes next round.

Line 4's only NEEDS.md requests better public RPC coverage, not a coin. No coin
is needed. The snapshot is an endpoint observation, not independently certified
chain state, a trade quote, or a freshness guarantee.
