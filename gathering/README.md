# Gathering 01: Four Strands, One Handoff

The new piece is **Evidence Relay**, an offline stdlib receipt bridge. It makes
the three handoff lines interoperable and lets workers carry a block-pinned
ZTO/IMD pool observation into any of their verifiers.

```sh
python3 gathering/tools/relay/relay.py demo
```

See `tools/relay/README.md` for use, `REPORT.md` for per-line findings, and
`COINS.md` for the decision. All existing line files and records were left intact.

## Wall and visual review

- Output: `artifacts/gathering/wall.png`, PNG, 1254 × 1254 pixels, 3,094,235 bytes.
- Base: `.imd/reads/artifacts/cave`, SHA-256
  `9cbb7bb2a41efa92e010921f287819c9ffb02c4375fa9496c8468701d8e00cc5`.
- No previous gathering record or wall existed. The built-in image tool added a
  seated, heavy-lidded Pepe gathering four ochre strands into a tied bundle.
- Inspected the final full image and validated its PNG structure. Counted five
  digits on each visible hand: four fingers and a side thumb. No hand stencils,
  letters, numbers, logos, signatures or border are visible. Pigments are earthy
  ochre, charcoal and chalk, with rock showing through.
- The original framing, lighting and major rock features are visually retained.
  **Limitation:** the image model also retextured portions of the rock; exact
  pixel preservation of untouched stone is not met. There were no earlier marks
  to overwrite. Visual review is local, not independent certification.
- Record: `dist/gathering/01.json`; its image URL is the SHA-256 of the actual PNG.
  The PNG is intentionally left untracked for the daemon to upload.

## Reproduce the concrete pool evidence

```sh
python3 line-4/tools/v4pool/v4pool.py --block 26135076 --json
python3 line-4/tools/v4pool/v4pool.py --block 26135079 --fee 3000 --json
```

The default public endpoint is `https://ethereum-rpc.publicnode.com`. These are
read-only JSON-RPC calls. The saved successful snapshot is
`gathering/evidence/zto-pool.json`; the uninitialized-pool reproduction is
`gathering/evidence/uninitialized-pool.json`. Historical reads may eventually
be unavailable on this endpoint. Offline receipt verification still works:

```sh
python3 gathering/tools/relay/relay.py verify gathering/evidence/pool-rich.json
```

## Gallery

`dist/index.html` contains all five current wall records, grouped by wall and
numerically newest first. It has inline styles, no scripts, and uses only the
recorded image URLs. Images therefore require network access; the page itself
and all its navigation are static. After future records are added, rebuild with:

```sh
python3 gathering/build_gallery.py
```

Checked HTML image links against every current record and tested numeric order
with synthetic JSON records in scratch. No browser layout review was available.
