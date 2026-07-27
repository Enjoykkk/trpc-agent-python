# Optimization Report

## Decision

REJECT

## Score Summary

{
  "validation_score": -0.3333333333333333,
  "cases": [
    {
      "case_id": "val_generalize_order_id",
      "change": "newly_failed",
      "score_delta": -1.0,
      "baseline_passed": true,
      "candidate_passed": false
    },
    {
      "case_id": "val_missing_order_id",
      "change": "unchanged",
      "score_delta": 0.0,
      "baseline_passed": false,
      "candidate_passed": false
    },
    {
      "case_id": "val_critical_refund",
      "change": "unchanged",
      "score_delta": 0.0,
      "baseline_passed": false,
      "candidate_passed": false
    }
  ]
}

## Gate Results

- validation score delta=-0.333
- new failures=['val_generalize_order_id']
- overfit=True
