# handoff-check

Create and verify portable SHA-256 evidence manifests offline, using Python 3's standard library. Any worker can carry a manifest alongside the named files and detect changed or missing bytes before continuing a task.

Run from the workspace root. Paths are relative to the current directory; use that same layout on the receiving worker. The tool rejects symlinks, absolute paths, parent traversal, duplicate manifest entries, and malformed schemas. It does not read environment variables, use the network, or execute evidence. Only explicitly named workspace files are read. Run it with the workspace as your current directory.

One command to see it working:

```sh
python3 line-1/tools/handoff-check/check.py demo
```

Create a manifest (stdout, with output redirected into your authorized folder):

```sh
python3 line-1/tools/handoff-check/check.py create line-1/GOAL.md line-1/tools/handoff-check/check.py > line-1/tools/handoff-check/example-manifest.json
python3 line-1/tools/handoff-check/check.py verify line-1/tools/handoff-check/example-manifest.json
```

Tried locally: the demo verified intact evidence, rejected modified evidence, and rejected traversal and absolute paths. Additional scratch checks rejected symlinks, missing files, and duplicate entries. The delivered example manifest verified two files. Failure returns exit status 1; success returns 0. Demo temporary files stay under this tool's directory and are removed automatically.

Limits: a hash proves agreement with the manifest, not authenticity, correctness, or safe contents. An attacker can replace both file and manifest. Obtain the manifest digest through a trusted channel. Verification assumes files are not concurrently modified; it is not a sandbox against hostile filesystem races. This first piece checks bytes; future pieces can add reproducible commands and structured evidence without executing untrusted instructions.
