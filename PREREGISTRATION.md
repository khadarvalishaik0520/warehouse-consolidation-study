# Pre-registration and deviation log

This file is the study plan as written during the work; each addendum and deviation is dated when it was written
(US Eastern time). It is reproduced verbatim except for 8 short phrases that named a separate study by the author;
those are replaced by text in [square brackets]. Experiment ids: F1 billing validation, F2/F2b size scaling, F3 replay,
F4 features and rule, F5 sensitivity.

---

# Paper 1 — Consolidate or Separate? A Billing-Exact Fleet Advisor for Cloud Data Warehouses
ICDE 2027 Industry & Applications · due **Tue Dec 1, 2026, 11:59 PM Pacific** · IEEE, 6 pp (long 12) + refs · author list frozen after acceptance

## Question (and only this question)
Which warehouses should exist: which workloads share, at what size, with what AUTO_SUSPEND -- minimum billed credits
within latency targets. Out of scope here [(belongs to a separate study)]: how a shared bill is split.

## Evidence [(no overlap with a separate study)]
- Main fleet evidence: **Snowset** (Snowflake, 2 weeks 2018, ~70M queries, warehouseId + warehouseSize).
  Consolidation candidates = warehouses that touch the same databaseId (same-customer proxy; no account id in Snowset).
  No suspend/resume events -> running periods reconstructed from query gaps under an assumed AUTO_SUSPEND (sweep 60–600 s).
- Snowflake calibration [(own runs, not reused elsewhere)]:
  (a) size scaling: TPCH10 query classes on XS/S/M -> runtime vs size per class;
  (b) suspend billing: scripted gaps around AUTO_SUSPEND -> model vs metered credits.
- Redset: not used.

## Advisor (to build)
Input: per-warehouse query intervals + sizes. Search over (grouping of warehouses into shared ones) x size x AUTO_SUSPEND.
Replay: runtime rescaled by the calibrated size model; queueing when concurrency exceeds the warehouse's capacity;
billed with the shared billing core. Objective: billed credits s.t. p95 latency inflation <= target per original warehouse.

## Frozen data definitions (2026-10-19 23:45 ET, before any F3–F5 number was computed; only a data inventory had been run)
- Query interval: [endTime - durationExec, endTime] (worker execution). Compile/scheduling excluded.
- Consolidation candidate group = >= 2 Snowset warehouses that each touch exactly one databaseId, the same one
  (same-customer proxy). Warehouses touching several databases are excluded from consolidation analysis.
- Inventory at freeze time: 2,051 warehouses, 69,182,074 queries; 1,215 single-database warehouses;
  190 databases with >= 2 such warehouses (= candidate groups).
- Billing replay: as-is size from warehouseSize; AUTO_SUSPEND grid {60, 300, 600 s} (Snowset has no suspend events).
- Advisor search space, queueing model and size model are still open; they will be frozen in a dated addendum
  before F3 runs.

## Addendum 1 (2026-10-20 06:45 ET, advisor design fixed before any F3–F5 run; only inventory counts seen)
- Groups analysed: candidate groups whose warehouses all keep one size for the two weeks (n_sizes = 1):
  134 of 190 (by size: 2 wh 89, 3 wh 22, 4 wh 10, 5 wh 3, 6 wh 5, 7 wh 1, 8+ wh 4). Mixed-size groups reported as excluded.
- Credits/hour = Snowset warehouseSize (1,2,4,...,64 = XS..3XL).
- Size model: exec_new = exec_old * (size_old/size_new)^alpha(c), class c by observed exec time
  (<1 s, 1–10 s, 10–60 s, >60 s); alpha(c) fitted on the F2 Snowflake XS/S/M runs. Advisor sizes limited to
  {size/2, size, 2*size} of the original warehouses (ratios inside the calibrated range). Until F2: alpha = 0.5 for
  all classes, used only for code tests, never reported.
- Queue model: each warehouse has 8 concurrent slots (Snowflake default MAX_CONCURRENCY_LEVEL), FIFO, no slowdown
  inside a slot (limitation; sensitivity with 4 slots). Resume adds 1 s to the first query after a suspend
  (sensitivity 0 s and 5 s). Cache effects not modelled (limitation).
- Latency target: for every original warehouse, p95 of (queue wait + resume delay + exec) <= 1.2 x its as-is p95
  under the same model (sensitivity 1.1 and 1.5).
- Search: partition of the group's warehouses x size x AUTO_SUSPEND {60, 300, 600}. Exhaustive for <= 4 warehouses;
  greedy pairwise merging (best feasible saving first) for larger groups; greedy-vs-exhaustive gap reported on <= 4.
- Baselines F3: (i) as-is (original size; as-is AUTO_SUSPEND assumed 600 = Snowflake default; also reported at 60, 300);
  (ii) separate, size tuned; (iii) separate, suspend tuned; (iv) consolidate-all, best feasible size; (v) advisor.
  Objective: billed credits = billed seconds / 3600 x credits/hour, billed with common/billing.py.

## Addendum 2 (2026-10-20 07:20 ET, F1/F2 Snowflake design fixed before any run)
- Arrival in replay = observed execution start in Snowset (original queueing folded in; limitation). Resume delay is billed.
- F2 (sf_f2.py) on ICDE_SZ (created for this paper only): sizes in ABBA order XS,S,M,M,S,XS; per block the 6 [TPC-H-style reporting]
  batch statements (corrected from 7 at preflight, 13:45 ET, before any run) + 6 heavier "ladder" statements on TPCH10, 3 reps round-robin; rep 0 after a resize = warm-up, not
  used. Exec time = QUERY_HISTORY execution_time. alpha(c) = median over statements in class c of
  log(t_XS / t_size) / log(size / XS) using S and M (reps 1-2, both ABBA halves). Class from the statement's median XS time.
  A class with < 2 statements takes the alpha of the nearest class with data (reported).
- F1 (sf_f1.py) on ICDE_SUSP (created for this paper only): probe statement with gaps 20,45,75,120,240 s (x2) at
  AUTO_SUSPEND 60, and 120,280,330,600,120,280,330 s at 300. Metric: model vs actual running periods
  (WAREHOUSE_EVENTS_HISTORY resume/suspend) and billed seconds vs metered credits.
- Warehouses (preflight 2026-10-20 13:44 ET): Snowflake Generation 2 (STANDARD_GEN_2), X-Small, query acceleration OFF,
  under CD_MONITOR. Snowset (2018) ran on older hardware -> state in the paper.
- Budget estimate: F2 1-3 credits, F1 < 0.5. Truth pulled by sf/pull_truth.py before the trial ends (~Nov 7).

## Addendum 3 (2026-10-20 13:55 ET) — F2b added; disclose in the paper
- Why: in F2's first block every statement took 0.1–3 s at XS (the [author's TPC-H-style] TPCH10 schema is small), so F2 can only
  calibrate classes 0–1; Snowset has many longer queries. Decided after seeing the XS block timings and 4 S-block timings;
  no alpha had been computed.
- F2b (sf_f2b.py): same protocol as F2 (ABBA XS,S,M,M,S,XS; 3 reps; rep 0 warm-up) on ICDE_SZ against
  SNOWFLAKE_SAMPLE_DATA.TPCH_SF100 with 6 statements (TPC-H Q1, Q6, Q3, Q18 shapes + 2 large aggregations); timeout 600 s.
  Runs after F2 (same warehouse). alpha(c) is fitted on F2 + F2b pooled, classes from XS median time as before.
- Budget estimate 2-3 credits.

## Addendum 4 (2026-10-20 20:25 ET) — F4 design, fixed before any feature value was computed
- Context (disclose): F3 is already analysed (claude/icde2027-fleet-advisor-results.md). The outcome threshold below was
  chosen after seeing F3; features, rule search and validation are fixed here before computing any feature.
- Unit: the 131 frozen groups where every option is feasible. Outcome PAYS = advisor's extra saving over the best
  single-knob baseline (min of size-tuned, suspend-tuned) > 5% of that baseline (26/131 positive in F3).
  Secondary outcome: the extra saving itself (continuous), Spearman correlation with each feature.
- Features, computed from Snowset query history only (no replay, no model): per warehouse over the two weeks
  (a) utilization = busy seconds (union of exec intervals) / (last end - first start);
  (b) resumes per day at AUTO_SUSPEND 60 = running periods per day under common/billing.py periods();
  (c) idle-tail share at 60 s = 1 - busy / billed seconds (billed under periods() with min 60 s);
  (d) overlap = share of the warehouse's running periods (60 s) that overlap another group member's running period;
  then per group: mean and min of (a)-(d) over members, k = number of warehouses, size spread = max size / min size,
  total billed credits at 60 s (scale).
- Rule search: (1) each single feature, best threshold by balanced accuracy; (2) depth-2 decision tree
  (min 5 groups per leaf). Both validated by leave-one-out cross-validation; report LOO balanced accuracy, precision and
  recall for PAYS, and the full-data rule as the stated rule. Baseline to beat: always "doesn't pay" (balanced acc 0.5).
- A priori expectation (stated before computing): pays when members are lightly used, resume often, have high idle-tail
  share, low overlap, similar size.
- Scripts: f4_features.py (Mac, Snowset), analyze_f4.py.

## Addendum 5 (2026-10-20 20:45 ET) — F5 variants fixed before any F5 run
- One-at-a-time changes to the F3 setup, frozen 134 groups, same analysis (analyze_f3.py, analyze_f4.py rule re-fitted and
  the F3 rule overlap_mean > 0.547 also applied unchanged):
  latency bound 1.1x and 1.5x; 4 slots; resume delay 0 s and 5 s; alpha x0.8 and x1.2 (all classes).
- Question per variant: does the ordering hold (suspend-tuned >> consolidation; median extra over best single knob ~0)
  and does overlap remain the top feature? Results reported as a robustness table, whatever they show.

## Pre-registered experiments (freeze before running)
- F1 Billing validation on Snowflake (suspend-gap script): |model - metered| / metered.
- F2 Size model fit: per class error of predicted runtime at S, M from XS (and leave-one-size-out).
- F3 Savings on Snowset vs baselines: (i) as-is; (ii) one warehouse each, tuned size only; (iii) tuned suspend only;
  (iv) consolidate-all; (v) advisor. Metrics: billed credits, % latency targets met.
- F4 When consolidation pays: savings vs the two warehouses' utilization and burst overlap -> a stated rule.
- F5 Sensitivity: assumed AUTO_SUSPEND, latency target, size-model error.

## Schedule [(interleaved with other work)]
- Wk1 Oct 20–26: Snowset loader + period reconstruction; advisor search design; freeze this plan.
- Wk2 Oct 27–Nov 2: Snowflake F1 + F2 runs (after credit check; [separate from other runs]).
- Wk3–4 Nov 3–16: F3–F5 on Snowset.
- Wk5 Nov 17–24: draft ([other work has priority this week]).
- Wk6 Nov 25–Dec 1: fact-check, co-authors final, submit Dec 1.

## Deviation 6 (2026-10-22 08:40 ET, found in the independent number check) — disclose where relevant
- analyze_f4.py's Spearman did not average tied ranks (about half the groups have extra saving = 0). Tie-corrected
  values are reported: overlap_mean +0.51 (was +0.49), k +0.30, size_spread -0.27, idle_share_mean -0.20,
  util_mean +0.13; across F5 variants +0.42 to +0.60. Rule, LOO accuracy and all savings are unaffected.
- F1 (Addendum 2 metric = model built from the probe statements): 60 s phase 7/7 periods, time ratio 0.994; 300 s
  4/4, 0.998. The earlier 1.083 counted every statement logged on ICDE_SUSP in the window, including an administrator's
  untagged metadata statements; reported as a secondary line, not the headline.

## Deviation 7 (2026-10-22 09:00 ET, from the independent review) — disclose in the paper
- analyze_f3.py/analyze_f4.py restricted every comparison to groups where ALL options were feasible, including consolidate-all.
  That drops 3 frozen groups (9, 17 and 2 warehouses) from comparisons that do not involve consolidate-all, among them the
  17-warehouse group where the joint search saves 70.3% over the best single knob (68.5% of all extra saving).
- Fix: compare as-is / size-only / suspend-only / joint search on all 134 groups (every one feasible); report consolidate-all
  on the 131 groups where it is feasible. Applied to F3, F4 (features, LOO rule) and every F5 variant (now all n = 134).
  Headline: suspend 23.7% (was 32.2%), joint 35.0% (was 37.4%), consolidation adds 14.8% of the best single-knob total
  (was 7.7%), pays in 27/134 groups by 5.1–70.3% (median 12.7%). LOO rule 0.759 / precision 0.67 / recall 0.59.
  Script: verify/icde_all134.py. The old 131-group numbers are reported as a sensitivity sentence.
- Also: alpha.json in the cloud working copy was the placeholder; fitted values restored from the results log (Mac copy is
  authoritative). Not reported (pre-registered, not computed): F2 leave-one-size-out error, greedy-vs-exhaustive gap,
  F1 billed-seconds-vs-metered-credits per hour beyond the 1.35 credits/h rate.

## Draft 4 expansion (2026-10-22, exploratory, not pre-registered) — labelled as such where relevant
- Size-model validation from alpha_fit.json: in-sample median error 12.4% (p90 44%); leave-one-size-out 12.4% / 24.8%;
  no-speed-up 60%, linear 35%.
- As-is timeout: joint saves 35.0% / 28.0% / 14.8% (vs 600 / 300 / 60 s); per-group median 61% / 46% / 0%.
- Case study 17-warehouse group (verify/case17.py): >=4 members running at every moment, 12.8 on average; 4,093
  separate warehouse-hours vs 960 merged; mean utilisation 0.42 vs fleet median 0.04.
- Top-8 groups hold 96% of consolidation saving; rule TP 18 (97.6% of saving), FN 9 (0.6%), FP 8 (median extra 0%,
  median size spread 4x).
- Overlap SQL (sql/overlap.sql = paper listing) reproduces overlap_mean exactly on the 7 groups testable locally.

## Draft for the research track, EAB (2026-10-27) — post-hoc analyses, reported as such
- Pre-registered secondary metric computed now: greedy vs exhaustive search on all 32 groups of 3-4 warehouses
  (verify/greedy_gap.py): identical cost in 32/32; re-run exhaustive equals the main run in 32/32.
- Exploratory: Proposition 1 tested on all 91 merged warehouses (verify/mechanism_test.py): equal-size merges realised
  1,342 vs 1,340 credits predicted (median ratio 1.003); mixed-size 12,998 vs 12,859 predicted; rate change costs 12,692.
- Exploratory: auto-suspend saving vs features (idle share +0.68, credits -0.75, utilisation -0.42, overlap -0.57);
  counter-example pair (verify/counterexample.py); savings by group size; per-period billing table.
