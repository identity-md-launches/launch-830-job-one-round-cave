# Handoff Check

Creates and verifies portable SHA-256 file manifests using Python 3.9+ standard library only. Run from the workspace root. It reads only explicitly named files within that workspace, refuses paths and symlinks resolving outside it, and uses no environment variables, network, wallets or secrets. The caller must select ordinary public deliverables, never secret files.

One command to see it working:

```sh
python3 line-2/tools/handoff-check/handoff.py demo
```

Create a manifest (stdout lets you choose an allowed destination), then verify it:

```sh
python3 line-2/tools/handoff-check/handoff.py create line-2/GOAL.md > line-2/tools/handoff-check/example.json
python3 line-2/tools/handoff-check/handoff.py verify line-2/tools/handoff-check/example.json
```

Exit codes: 0 means all listed files match, 1 means a file is missing or changed, 2 means invalid input or an I/O error. Paths are relative to the workspace, not the manifest. Unlisted files are not checked. A manifest proves byte consistency, not authorship, safety or truth; obtain the expected manifest through a trusted handoff. Files must remain stable while being checked.

Trial results: the in-memory demo accepted intact bytes and detected changed bytes. Scratch tests also exercised real-file creation/verification, tampering, missing files, traversal, escaping symlinks and malformed records; all passed. No network or third-party package was needed.
