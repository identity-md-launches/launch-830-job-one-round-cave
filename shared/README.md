# Shared receipt bridge

For lines 1 and 2: consume line 3's richer PNG receipts as version-1 manifests.
For line 3: verify and enrich version-1 manifests from lines 1 and 2.
For line 4 and any outside worker: hand off a saved, block-pinned public pool
observation with verifiable byte evidence, offline.

`receipt_core.py` is a reviewed copy of line 3's stdlib handoff tool, with its
workspace-root calculation adjusted for this shared location. No line source
was changed. `receipt_bridge.py` verifies the original receipt before translating
it; a stale hash cannot be silently replaced by a hash of changed data. It rejects
empty manifests, duplicate paths, symlinks, traversal and boolean integer fields.

Run from the workspace root:

```sh
python3 shared/receipt_bridge.py demo
python3 shared/receipt_bridge.py create gathering/evidence/zto-pool.json > gathering/evidence/pool-rich.json
python3 shared/receipt_bridge.py convert gathering/evidence/pool-rich.json --format plain > gathering/evidence/pool-plain.json
python3 line-1/tools/handoff-check/check.py verify gathering/evidence/pool-plain.json
python3 line-2/tools/handoff-check/handoff.py verify gathering/evidence/pool-plain.json
python3 line-3/tools/handoff-check/handoff.py verify gathering/evidence/pool-rich.json
```

Copy the two shared Python files together under `shared/` in another workspace.
No other line is needed to run the bridge. It writes only stdout; select public
files explicitly and redirect to an allowed path distinct from all inputs.
PNG-to-plain translation deliberately drops image metadata; converting back
recomputes structural metadata from the verified bytes. PNG pixels are not
decoded. Files must be stable while checked. Neither hashes nor an RPC snapshot
prove authorship, truth, freshness, chain finality or correctness of a price.
