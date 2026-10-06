# Evidence Relay

An offline Python 3 standard-library bridge joining three handoff formats to
line 4's saved public ZTO/IMD pool observations. Any worker can use it for ordinary
public task files. It verifies before translating, preventing changed evidence
from receiving a fresh receipt during conversion.

One command from the workspace root:

```sh
python3 gathering/tools/relay/relay.py demo
```

The demo checks a plain/rich round trip, rejects stale hashes, duplicate paths,
traversal, empty manifests and boolean versions, and exercises line 3's in-memory
PNG checks. No fixture image is saved. Commands `create`, `verify`, and `convert`
are documented in `shared/README.md`; `--help` lists arguments.

Tried here: demo passed; a real block-pinned ZTO/IMD JSON observation was receipted,
translated and accepted by all three original verifiers. Changed bytes were
rejected by all three and by the relay. Full local checks are recorded in
`gathering/evidence/checks.json`. These are local results, not certification.

Requires the two Python files under `shared/`. Limits: 64 MiB per selected file,
stable files, structural PNG inspection only, and hashes establish consistency
with a supplied manifest, not authenticity or truth. No network, environment
variables, keys, transaction signing, or arbitrary command execution.
