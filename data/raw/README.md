# Raw data is intentionally not committed

Place the following real, user-supplied files in the directory selected by
`MACRO_STRATEGY_DATA_DIR`, or leave that variable blank to use the project root:

- `China Rolled Return.csv`
- `China Rolled Return2.csv`
- `china-data.csv`
- `data_indicator_review.csv`

Their current source, redistribution permission, and point-in-time provenance
are unconfirmed. The local originals are preserved at the project root and are
listed in `docs/data_manifest.json`, but `.gitignore` excludes them from upload.

Production runs never download replacements and never fall back to sample,
mock, random, synthetic, interpolated, or legacy result data.

