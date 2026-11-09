# Public release verification

Executed by Codex on 2026-11-09 with Python 3.11.16, pandas 2.3.3, Streamlit 1.67.0 and SQLite 3.53.4.

- Public demo suite: 6 tests; no personal saves required.
- Combined local suite: 21 tests passed, including 15 private integration/presentation checks. Private fixtures/results remain untracked.
- Actual Chrome checks in default synthetic mode verified the source label and each main module: economy, activity/XP, comparison chart and data quality. Demo balances, shipping totals, XP differences and Insights were computed from the shipped synthetic XML.
- Browser review caught two data-dependent wording assumptions (all skills being maxed and ID coverage exceeding unit coverage). Both were replaced with data-independent, accurate interpretation text.
- The synthetic fixtures are minimal parser inputs, not playable game saves and not reconstructed personal history.
- No claim of real retention, cohort, LTV or A/B-test evidence is made. Agent checks are separate from owner browser acceptance.

Run:

```sh
python -m unittest discover -s tests -p 'test_public_demo.py' -v
```

Only public files are staged for release. Raw saves, private reports/tests, environment files, caches and databases are excluded. No raw save is needed for a clean checkout's default dashboard.
