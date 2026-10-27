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
- `analysis/paper_numbers.py` — as-is timeout comparison, size-model accuracy, top-8 table, rule errors, joint-plan composition;
- `sf/validate_f1.py` — billing validation table (model vs Snowflake resume/suspend events);
- `paper/make_figs.py` — figures 2, 3, 5 and the per-group figure;
- `analysis/case17.py` — the 17-warehouse case study and its figure (needs the Snowset intervals below).

`icde27_fleet/analyze_f3.py` and `analyze_f4.py` are the analyses as pre-registered; they restrict comparisons to groups
where every option is feasible, which the paper corrects (see Deviation 7 in `PREREGISTRATION.md`).

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

## Data

Snowset: Vuppalapati et al., *Building An Elastic Query Engine on Disaggregated Storage*, NSDI 2020.

## License

MIT (code). Snowset is distributed by its authors under their own terms.
