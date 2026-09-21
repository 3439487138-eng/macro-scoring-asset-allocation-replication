# Reproducibility notes

## Boundaries

- Production reads only the four configured real source files.
- Existing CSV, PNG, XLSX, pickle, and notebook outputs are `legacy_unverified`.
- Tests use isolated micro fixtures and cannot satisfy a production run.
- Report generation is downstream of validation and a real backtest; failures publish nothing.

## Paper Replicator skill

- Source: local `paper-replicator` skill supplied by the execution environment.
- Git revision: unavailable at audit time.
- `SKILL.md` SHA256: `A086CE12A88874C66B1CE006169B343F2151552001B8B1E3BFB5E446CEA6260F`.

## Verification required before claiming reproduction

1. Resolve `CREDIT` versus `SHORT_BOND` without inference.
2. Supply monthly real oil and loan observations, or approve a separately labelled reduced-scope adaptation.
3. Replace or formally approve the bond return input semantics.
4. Resolve duplicate macro keys using source-defined economic aggregation.
5. Confirm the domestic FX lag interpretation.
6. Confirm data provenance and redistribution rights.
7. Run from an isolated checkout without legacy outputs and inspect the generated report.
8. Manually dispatch GitHub Actions and verify its artifact and same-branch commit.

Until all applicable items are complete, the correct status is **reproduction incomplete**.

One possible owner-approved amendment is to declare an explicit
`CREDIT = SHORT_BOND` alias in configuration, with its evidence and approval
recorded in the run manifest. It is not the default, is not implemented now,
and must not be described as cash or as an unchanged original replication.
