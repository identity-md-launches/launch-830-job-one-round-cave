# Handoff Check

A small offline receipt generator and verifier for any worker handing files to another worker. It records exact byte lengths and SHA-256 hashes, plus PNG dimensions and limited structural checks when applicable. Python 3 standard library only. No network, environment-variable access, transactions, or automatic directory scanning. It reads only explicitly named regular files inside this workspace, rejecting symlink paths and parent traversal. It prints JSON and does not write files itself.

Run from the repository root:

```sh
python3 line-3/tools/handoff-check/handoff.py demo
```

The demo makes a one-pixel PNG entirely in memory. When tried, it accepted that PNG, rejected three malformed variants (truncation, trailing bytes, wrong CRC), verified its own source receipt, rejected a tampered hash, and rejected absolute and parent-traversal paths. It saves no fixture.

Additional scratch checks rejected an actual changed file, a symlink input, and four malformed receipt shapes. These are local self-checks, not independent certification.

Run the included regression checks with `python3 line-3/tools/handoff-check/test_handoff.py`. They create no files and cover the in-memory demo, metadata tampering, malformed receipts, and duplicate paths.

Create a receipt, then check it against the current files:

```sh
python3 line-3/tools/handoff-check/handoff.py create artifacts/line-3/wall.png line-3/GOAL.md > artifacts/line-3/receipt.json
python3 line-3/tools/handoff-check/handoff.py verify artifacts/line-3/receipt.json
```

Paths are always relative to the workspace root inferred from this tool's location under `line-3/tools/handoff-check/`. Keep that layout when copying it. Files are limited to 64 MiB. Exit status is zero on success, one for invalid data or a mismatch, and two for invalid command arguments. Redirect output only to an allowed workspace path, distinct from every input. Explicitly select public deliverables; do not feed it secrets. Run on a stable tree without concurrent writers.

PNG checks cover the signature, chunk lengths and CRCs, IHDR fields, consecutive IDAT chunks, and terminal IEND. This is deliberately **not** a complete PNG validator: it does not decompress pixels, enforce every ancillary chunk rule, or certify appearance. `pixels_decoded: false` makes that limit explicit. Matching hashes prove equality to the supplied receipt, not authorship, safety, completeness, or correctness. Obtain a trusted receipt separately when trust matters. An attacker replacing both files and receipt defeats this check.

This first piece establishes reproducible byte evidence. Future pieces can add semantic checks and explicit requirements without replacing the stable receipt format. No coin or payment is needed for this offline tool.
