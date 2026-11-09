# Stardew Valley Analytics Lab

A small interactive analytics portfolio: **Python XML parsing → pandas → SQLite SQL → Streamlit**. Warm farm-inspired colors; no extracted game artwork. Independent project, not affiliated with the game publisher or Rovio.

## Public demo versus private analysis

**Default: SYNTHETIC DEMO.** Two tiny XML fixtures in `demo/` were authored from scratch for software demonstration. Their farm name, dates, item IDs, characters, balances and activity counts are fictional. They are not anonymized exports, actual player behavior or evidence of real business outcomes. All dashboard values, charts and Data Insights are computed from the selected fixtures; none are copied from private results. Public startup does not inspect your game directory.

**Optional private mode:** the parser was also exercised locally against an authorized personal main save and its previous backup. Raw saves, private reports, private baseline tests, personal identifiers and absolute local paths are excluded from publication. To analyze your own local data, explicitly set `STARDEW_SAVE_DIR` to a save folder containing a file with the same name as that folder and its `_old` counterpart. Only run this on localhost; never upload the files. Do not set this variable for the public demo.

The app opens XML **read-only**, keeps pandas tables and SQLite in memory, and does not copy saves or persist database exports. Do not run the game while comparing endpoints: concurrent file changes could yield an inconsistent pair. XML input must be locally trusted; this is not a public upload service for untrusted XML.

## Run the self-contained public demo

Python 3.11 is the verified runtime.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8503
```

Open **http://127.0.0.1:8503**. No game, Steam, personal saves, account, API key or data download is needed. Leave `STARDEW_SAVE_DIR` unset to use the public fixtures. Dependencies are ranged rather than fully locked. The repository contains all fixture files needed to run the demo.

## Three analysis modules

- **Farm Economy:** gold balance, recorded lifetime earnings, item-level shipping mix, backpack item quantities/quality, current saved crop nodes. Item names are inferred only from unambiguous explicit Object ID/name pairs in the XML. Unmapped IDs remain visible. Backpack includes equipment, not all farm stock or saleable inventory.
- **Player Activity & Progression:** recorded skill XP differences, optional endpoint skill levels/XP totals, fishing/mining/gifting/quest counters, social state and achievement IDs.
- **Snapshot Comparison:** endpoint changes in balance, lifetime earnings, recorded time, matched cumulative counters and skill XP. A horizontal chart labels non-zero activity changes with exact units and raw fields.

**Data Quality & SQL** supports all three: missing/empty fields, invalid numbers, duplicate dictionary IDs, negative counts, unusual skill levels, ambiguous names, mapping coverage and shipping scope reconciliation. Actual queries use a shipping CTE/LEFT JOIN/GROUP BY, matched-counter CTE/JOIN and mapping-completeness LEFT JOIN. Friendly labels retain raw field IDs for audit.

## Metric definitions and limits

- `money` is an endpoint balance; `totalMoneyEarned` is a recorded cumulative field. Neither establishes profit. No complete spending ledger or realized sale-price history is available.
- `basicShipped` item totals and `itemsShipped` counters can differ in scope. The demo deliberately includes such a mismatch to exercise reconciliation; it is labeled synthetic, not presented as a measured real-game outcome. Both values remain unchanged.
- Empty legacy stat nodes are not zeros: actual counters come from `stats/Values`. Missing counters are not filled with zero. Differences use a matched JOIN.
- Inventory is backpack-only; no chest/machine/fridge inventory valuation is claimed. Crop nodes are current XML state, not historical harvests or necessarily unique outdoor farm tiles.
- Item-name coverage is reported both by ID count and by shipped units. Achievement names or completion percentages are not guessed without a verified catalog.
- Snapshot deltas are not a complete transaction/event log. Steps, fish, gifts and shipped items have different units; they must not be summed into engagement. Observations do not establish causal income effects.
- One farm with two snapshots is not a user cohort. This project does **not** claim retention, cohort analysis, LTV forecasting, A/B testing or long-term player-event reconstruction.

## Verification

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_public_demo.py' -v
```

The public tests need no private data. They check demo-only file access, schema/date/balance consistency, SQL aggregation and mapping coverage, unit-labeled differences, XP, quality disclosures, and Streamlit AppTest with both snapshot selections. See `PUBLIC_TESTING.md` for executed results. Private integration records are kept locally and excluded from Git.

## Contributions

**Project owner:** proposed the project direction, chose analysis questions and feature requirements, reviewed outputs and requested presentation improvements. Personal final acceptance remains separate from agent verification.

**Codex:** implemented Python parsing, pandas tables, SQL, Streamlit presentation and synthetic fixtures; wrote and ran automated checks and performed browser checks. Code presence is not a claim that the owner independently wrote or tested it, or has professional game-industry experience.

## License and privacy

Code and authored synthetic fixtures are provided under the MIT license. Stardew Valley names and game rights belong to their respective owners. No game artwork, raw personal saves or private gameplay exports are distributed. Review any future screenshots/exports before publishing; never expose private mode as a public service.
