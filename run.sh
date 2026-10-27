#!/bin/bash
# Reproduce the replay results (needs data/snowset_iv from ./get_data.sh). Long-running: hours on a laptop.
#   ./run.sh f3          main replay -> icde27_fleet/results/f3.jsonl
#   ./run.sh f4          group features -> icde27_fleet/results/f4_features.jsonl
#   ./run.sh f5 <v>      sensitivity variant, v in: t11 t15 s4 r0 r5 a08 a12
#   ./run.sh analysis    every number, table and figure in the paper from the result files (minutes)
set -eu; cd "$(dirname "$0")"
F3="python3 -u icde27_fleet/run_f3.py data/snowset_iv icde27_fleet/results icde27_fleet/alpha.json"
case "${1:-}" in
  f3) $F3 ;;
  f4) python3 -u icde27_fleet/f4_features.py data/snowset_iv icde27_fleet/results/f4_features.jsonl ;;
  f5) case "${2:-}" in
        t11) $F3 --target 1.1 --tag f5_t11 ;;  t15) $F3 --target 1.5 --tag f5_t15 ;;  s4) $F3 --slots 4 --tag f5_s4 ;;
        r0) $F3 --resume 0 --tag f5_r0 ;;  r5) $F3 --resume 5 --tag f5_r5 ;;
        a08) $F3 --alpha-scale 0.8 --tag f5_a08 ;;  a12) $F3 --alpha-scale 1.2 --tag f5_a12 ;;  *) sed -n 2,6p "$0" ;; esac ;;
  analysis) python3 analysis/icde_all134.py; python3 analysis/icde_review2.py; python3 analysis/paper_numbers.py
            python3 sf/validate_f1.py; (cd paper && python3 make_figs.py)
            [ -d data/snowset_iv ] && python3 analysis/case17.py || echo "case17.py skipped (needs data/snowset_iv)" ;;
  *) sed -n 2,6p "$0" ;;
esac
