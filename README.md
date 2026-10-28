# Consolidate or Separate? — artifacts

Code, data-preparation scripts, raw results, Snowflake calibration logs and the pre-registration for the paper
*Consolidate or Separate? Usually Neither: When Merging Cloud Data Warehouses Pays*.

The study replays two weeks of Snowflake's public fleet trace (Snowset) for 134 groups of warehouses under an exact
per-second billing model, and asks when merging warehouses saves money compared with tuning auto-suspend or resizing.

## What is here

| Path | Contents |
|---|---|
| `PREREGISTRATION.md` | Study plan with dated addenda and every deviation, as written during the work |
| `common/billing.py` | Billing model: running periods, per-second billing with the 60 s minimum |
| `icde27_fleet/` | Snowset loader, replay and search (`advisor.py`, `run_f3.py`), features (`f4_features.py`), pre-registered analyses (`analyze_f3.py`, `analyze_f4.py`), size-model fit (`fit_alpha.py`, `alpha.json`, `alpha_fit.json`), the 134 frozen groups |
| `icde27_fleet/results/` | Raw result files: `f3.jsonl` (main replay), `f4_features.jsonl`, `f5_*.jsonl` (seven sensitivity variants) |
| `icde27_fleet/sql/overlap.sql` | The overlap check printed in the paper |
| `sf/` | Snowflake calibration: run scripts (`../icde27_fleet/sf_f1.py`, `sf_f2.py`, `sf_f2b.py`), raw run logs (`runs/`), Snowflake's own records for the two calibration warehouses (`truth/`), and `validate_f1.py` |
| `analysis/` | Scripts that produce every number in the paper from the result files |
| `paper/` | LaTeX source, figures and `make_figs.py` |
| `tests/` | Unit tests for the billing model and the replay/search |

## Reproduce the paper's numbers (minutes, no Snowset download needed)

```
pip install -r requirements.txt
python3 tests/test_billing.py && python3 tests/test_advisor.py
./run.sh analysis
```

`./run.sh analysis` runs:

- `analysis/icde_all134.py` — headline savings, consolidation results, feature correlations, leave-one-out rule, sensitivity table (all 134 groups);
- `analysis/icde_review2.py` — results without the largest groups; the rule at 3%, 5% and 10% thresholds;
- `analysis/paper_numbers.py` — as-is timeout comparison, size-model accuracy, top-8 table, rule errors, joint-plan composition, savings by group size, drivers of the auto-suspend saving, greedy-vs-exhaustive gap and the Proposition 1 test;
- `sf/validate_f1.py` — billing validation table (model vs Snowflake resume/suspend events);
- `paper/make_figs.py` — every figure drawn from the result files (savings, per-group, as-is timeout, overlap, Proposition 1 test);
- `analysis/case17.py` and `analysis/counterexample.py` — the two timeline figures, from the small Snowset extracts in
  `data/extracts/` (the same rows as the full trace for those two groups).

Three further scripts re-derive inputs that `paper_numbers.py` summarises; they need the full Snowset intervals:

- `analysis/greedy_gap.py` — greedy vs exhaustive search on the 32 groups of 3-4 warehouses (writes `results/greedy_gap.jsonl`);
- `analysis/mechanism_test.py` — Proposition 1: realised vs predicted saving of every merged warehouse (writes `results/mechanism.jsonl`);
- `analysis/greedy_gap_large.py` — exhaustive vs greedy search on the 10 groups of 5-8 warehouses (writes `results/greedy_gap_large.jsonl`).

`icde27_fleet/analyze_f3.py` and `analyze_f4.py` are the analyses as pre-registered; they restrict comparisons to groups
where every option is feasible, which the paper corrects (paper deviation (3); `PREREGISTRATION.md`, Deviation 7). `analysis/pays_v2.py` applies the
revised definition of "consolidation pays" used in the paper (paper deviation (7); Deviation 8) and prints the table of
paying groups.

## Re-run the replay (hours)

```
./get_data.sh          # downloads Snowset (about 8 GB) and builds data/snowset_iv/
./run.sh f3            # main replay
./run.sh f4            # group features
./run.sh f5 s4         # one sensitivity variant; also t11 t15 r0 r5 a08 a12
```

## Snowflake calibration

The billing-validation and size-scaling runs used a personal Snowflake trial account with two dedicated X-Small
Generation 2 warehouses (`sf/setup_warehouses.sql`). Credentials are read from `~/.snowflake/connections.toml`
(connection `cdexp`); none are stored here. F1 and F2 ran on schemas `TPCH` and `TPCH10` of a database `CDEXP` holding the
author's TPC-H-style tables; F2b ran on Snowflake's `SNOWFLAKE_SAMPLE_DATA.TPCH_SF100`. Timings on another account will
differ; the raw logs and Snowflake's own records from our runs are in `sf/runs/` and `sf/truth/`.

## Pre-registered additions (Addenda 7 and 8, 2026-10-27)

- `icde27_fleet/f7/` — time-split test of the overlap rule: fit on week 1, test on week 2 (`run_split.py`, `analyze_split.py`).
- `icde27_fleet/f6/` and `icde27_fleet/sf_f6.py` — a real merge on Snowflake: three Snowset windows (high overlap, partial
  overlap, turn-taking) run separately and merged on nine X-Small warehouses (`sf/setup_f6.sql`). The window scan,
  selection rule, schedule (`schedule.json`) and predictions were committed before the run.
- Results: the real merges saved 49.8%, 20.1% and 0.0% of metered credits (predicted 49.8%, 20.0%, 0.0%); raw logs in
  `sf/runs/f6_*.jsonl`, Snowflake's records in `sf/truth/f6_*.csv`. The week-1 rule predicts week-2 outcomes with balanced
  accuracy 0.86-0.88. Both are printed by `./run.sh analysis`.

## Data

Snowset: Vuppalapati et al., *Building An Elastic Query Engine on Disaggregated Storage*, NSDI 2020.

## License

MIT (code). Snowset is distributed by its authors under their own terms.
