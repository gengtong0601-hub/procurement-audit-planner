#!/usr/bin/env python3
"""Independently re-derive one real flagged item per indicator from cleaned CSVs."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path


def read(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def run(analytics_path: Path, full: Path) -> dict:
    summary = json.loads(analytics_path.read_text())
    rows = read(full / "spend-clean.csv")
    notices = read(full / "notices-clean.csv")
    lookup = {r["row_id"]: r for r in rows}
    results = []
    months = summary["population"]["months_covered"]

    def add(test, ok, ids, details):
        results.append({"test": test, "passed": bool(ok), "row_ids": ids, "independent_check": details})

    flags = read(full / "threshold-clustering.csv")
    if flags:
        f = flags[0]
        r = lookup[f["row_id"]]
        value = int(f["threshold_pence"])
        threshold = next(t for t in summary["thresholds"] if t["amount_pence"] == value)
        amount = int(r["amount_pence"])
        add("threshold_clustering", amount * 10 >= value * 9 and amount < threshold["effective_trigger_pence"], [r["row_id"]], {"amount_pence": amount, "threshold_pence": value})
    flags = read(full / "split-purchases.csv")
    if flags:
        f = flags[0]
        start = date.fromisoformat(f["window_start"])
        trigger = int(f["effective_trigger_pence"])
        selected = [r for r in rows if r["supplier_norm"] == f["supplier_norm"] and start <= date.fromisoformat(r["pay_date"]) < start + timedelta(days=30) and int(r["amount_pence"]) < trigger]
        ids = sorted(r["row_id"] for r in selected)
        total = sum(int(r["amount_pence"]) for r in selected)
        add("split_purchases", len(selected) >= 2 and total >= trigger and total == int(f["amount_pence"]) and ids == sorted(f["row_ids"].split(";")), ids, {"recomputed_pence": total, "trigger_pence": trigger})
    flags = read(full / "high-value-suppliers.csv")
    if flags:
        f = flags[0]
        selected = [r for r in rows if r["supplier_norm"] == f["supplier_norm"]]
        total = sum(int(r["amount_pence"]) for r in selected)
        threshold = min((t for t in summary["thresholds"] if t["competition_triggering"]), key=lambda t: t["amount_pence"])
        add("high_value_suppliers", total == int(f["amount_pence"]) and total * 12 >= threshold["effective_trigger_pence"] * months, [r["row_id"] for r in selected], {"recomputed_pence": total, "months": months})
    flags = read(full / "duplicates.csv")
    if flags:
        f = flags[0]
        ids = f["row_ids"].split(";")
        selected = [lookup[i] for i in ids]
        dates = [date.fromisoformat(r["pay_date"]) for r in selected]
        amounts = {int(r["amount_pence"]) for r in selected}
        tier = "same_timestamp" if len({r["Date"] for r in selected}) == 1 else "different_time"
        excess = int(selected[0]["amount_pence"]) * (len(selected) - 1)
        add("duplicates", len(amounts) == 1 and len({r["supplier_norm"] for r in selected}) == 1 and (max(dates) - min(dates)).days <= 7 and excess == int(f["excess_pence"]) and tier == f["tier"], ids, {"recomputed_excess_pence": excess, "tier": tier})
    flags = read(full / "off-contract-unmatched.csv")
    if flags:
        f = flags[0]
        selected = [r for r in rows if r["supplier_norm"] == f["supplier_norm"]]
        total = sum(int(r["amount_pence"]) for r in selected)
        active = [n for n in notices if n["active"] == "True" and n["starts_after_window"] != "True"]
        register = read(full / "register-clean.csv")
        active += [r for r in register if r.get("active") == "True"]
        exact = any(n["supplier_norm"] == f["supplier_norm"] for n in active)
        threshold = Decimal(str(summary["tests"]["off_contract"]["parameters"]["publication_threshold"])) * 100
        add("off_contract", not exact and total * 12 >= threshold * months and total == int(f["amount_pence"]), [r["row_id"] for r in selected], {"recomputed_pence": total, "no_exact_active_notice": not exact})
    flags = read(full / "expired-notice-spend.csv")
    if flags:
        f = flags[0]
        matched = [n for n in notices if n["supplier_norm"] == f["supplier_norm"]]
        total = sum(int(r["amount_pence"]) for r in rows if r["supplier_norm"] == f["supplier_norm"])
        okay = bool(matched) and all(n["contract_end"] and n["contract_end"] < summary["population"]["date_min"] for n in matched)
        add("expired_notice_spend", okay and total == int(f["amount_pence"]), f["row_ids"].split(";"), {"recomputed_pence": total, "all_exact_notices_ended": okay})
    flags = read(full / "spend-vs-award.csv")
    if flags:
        f = flags[0]
        notice = next(n for n in notices if n["notice_id"] == f["notice_id"])
        days = (date.fromisoformat(notice["contract_end"]) - date.fromisoformat(notice["contract_start"])).days + 1
        total = sum(int(r["amount_pence"]) for r in rows if r["supplier_norm"] == f["supplier_norm"])
        ratio = Decimal(total) * 12 / months / (Decimal(notice["award_pence"]) * Decimal("365.25") / days)
        add("spend_vs_award", ratio >= Decimal("1.25") and abs(ratio - Decimal(f["ratio"])) <= Decimal("0.000001") and int(notice["suppliers_on_notice"]) == 1, f["row_ids"].split(";"), {"recomputed_ratio": str(ratio), "notice_id": f["notice_id"]})
    payload = {"producer": "Codex preparation; independent Python arithmetic checks, not Claude Code verification", "passed": all(r["passed"] for r in results), "checks": results,
               "unavailable_checks": [name for name, item in summary["tests"].items() if item.get("skipped") or item.get("count", 0) == 0]}
    (full / "selfcheck.json").write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--analytics", type=Path, default=Path("outputs/analytics.json"))
    p.add_argument("--full", type=Path, default=Path("outputs/analytics-full"))
    a = p.parse_args()
    result = run(a.analytics, a.full)
    for check in result["checks"]:
        print(f"{'PASS' if check['passed'] else 'FAIL'} {check['test']}: {len(check['row_ids'])} source rows independently reconciled; first row {check['row_ids'][0]}")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
