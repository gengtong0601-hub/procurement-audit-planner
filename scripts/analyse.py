#!/usr/bin/env python3
"""Deterministic procurement risk indicators; Python computes, auditors judge.

Run clean.py first. Threshold values come only from rules.json. Each output
is an indicator, not a finding, and carries source workbook row identifiers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from difflib import SequenceMatcher
from pathlib import Path

from clean import InputError, NOTICE_CAVEAT, gbp, read_csv, to_pence, write_csv, write_json

GENERIC = set("AND OF THE SERVICES SERVICE GROUP CARE COMPANY HOMES HOME HOUSE UNIVERSITY COUNCIL TRUST SOLUTIONS CONSULTANCY CONSULTING ASSOCIATES PARTNERSHIP NETWORK CENTRE CENTER TRAVEL CARS COACHES TAXIS CONSTRUCTION HEALTHCARE HEALTH SCHOOL SCHOOLS EDUCATION SUPPORT LIVING CHILDREN CHILDRENS SEN BERKSHIRE WEST SOUTH NORTH EAST READING NEWBURY THATCHAM HUNGERFORD SOUTHERN SYSTEMS SOFTWARE HOUSING SECURITY CLEANING FOSTERING COMMUNITY BUSINESS MANAGEMENT FACILITIES SUPPLIES CATERING TRANSPORT ENGINEERING HIRE PROPERTY PROPERTIES VALLEY".split())
COMPETITION_RE = re.compile(r"\bquot(?:e|es|ations?|ing)\b|\btender|\bcompetiti", re.I)
TAGS = ("general_procurement", "care_or_education_placement", "grant", "agency_staff", "premises_non_procurement")


def annualised_pence(total: int, months: int) -> int:
    return int((Decimal(int(total)) * 12 / months).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def is_true(value) -> bool:
    return value is True or str(value).lower() == "true"


def stable_id(prefix: str, parts: list[str]) -> str:
    return prefix + "-" + hashlib.sha256("|".join(parts).encode()).hexdigest()[:14]


def load_rules(path: Path) -> tuple[dict, list[dict], list[dict]]:
    if not path.exists():
        raise InputError(f"Missing rules input: {path}")
    doc = json.loads(path.read_text())
    if isinstance(doc, list):
        doc = {"rules": doc, "parameters": {}}
    if not isinstance(doc.get("rules"), list) or not doc["rules"]:
        raise InputError("rules.json must contain a non-empty rules array")
    parameters = doc.get("parameters", {})
    thresholds, skipped = {}, []
    for name, record in parameters.items():
        if (record.get("value") if isinstance(record, dict) else record) is None:
            skipped.append({"test": "threshold_dependent_tiers", "tier": name, "reason": f"{name} is null; no value invented"})
    for rule in doc["rules"]:
        if rule.get("type") not in {"threshold", "approver", "anti-avoidance"}:
            continue
        rid = rule["rule_id"]
        competition = rule.get("competition_triggering")
        if not isinstance(competition, bool):
            competition = bool(COMPETITION_RE.search(rule.get("required_action", "")))
        for side in ("low", "high"):
            value = rule.get(f"threshold_{side}")
            reference = rule.get(f"threshold_{side}_ref")
            if reference:
                parameter = parameters.get(reference, {})
                value = parameter.get("value") if isinstance(parameter, dict) else parameter
            if value is None:
                continue
            pennies = to_pence(value, f"{rid}.threshold_{side}")
            if pennies <= 0:
                continue
            entry = thresholds.setdefault(pennies, {"value": gbp(pennies), "amount_pence": pennies, "rule_ids": [], "competition_triggering": False, "boundaries": [], "parameter_refs": []})
            entry["rule_ids"].append(rid)
            entry["competition_triggering"] |= competition
            inclusive = rule.get(f"threshold_{side}_inclusive")
            entry["boundaries"].append({"rule_id": rid, "side": side, "inclusive": inclusive, "competition_triggering": competition, "scope": rule.get("scope", "all")})
            if reference:
                entry["parameter_refs"].append(reference)
    for entry in thresholds.values():
        lowers = [b for b in entry["boundaries"] if b["side"] == "low" and b["competition_triggering"]]
        lowers = lowers or [b for b in entry["boundaries"] if b["side"] == "low"]
        # At a shared boundary, the next tier's lower bound controls the trigger.
        entry["inclusive"] = any(b["inclusive"] is True for b in lowers) if lowers else not all(b["inclusive"] is True for b in entry["boundaries"])
        entry["effective_trigger_pence"] = entry["amount_pence"] + (0 if entry["inclusive"] else 1)
        entry["rule_ids"] = sorted(set(entry["rule_ids"]))
        entry["parameter_refs"] = sorted(set(entry["parameter_refs"]))
    if not thresholds:
        raise InputError("No usable numeric thresholds in rules.json")
    return doc, [thresholds[k] for k in sorted(thresholds)], skipped


def publication_threshold(rules: dict) -> dict | None:
    """Derive the publication floor from a rule that actually requires notice publication."""
    candidates = []
    for rule in rules["rules"]:
        action = rule.get("required_action", "")
        if re.search(r"publish|publication", action, re.I) and re.search(r"notice|advert", action, re.I) and rule.get("threshold_low") is not None:
            candidates.append({"value": rule["threshold_low"], "amount_pence": to_pence(rule["threshold_low"]),
                               "inclusive": rule.get("threshold_low_inclusive") is True, "rule_ids": [rule["rule_id"]]})
    if not candidates:
        return None
    floor = min(candidates, key=lambda x: x["amount_pence"])
    floor["rule_ids"] = sorted({rid for c in candidates if c["amount_pence"] == floor["amount_pence"] for rid in c["rule_ids"]})
    return floor


def rule_ids_for(rules: dict, clause: str) -> list[str]:
    return [r["rule_id"] for r in rules["rules"] if r.get("clause", "").casefold() == clause.casefold()]


def restore_spend(rows: list[dict]) -> list[dict]:
    for row in rows:
        row["amount_pence"] = int(row["amount_pence"])
        row["source_row"] = int(row["source_row"])
        if not row["row_id"] or not row["supplier_norm"] or row["Supplier name"].casefold() == "redacted":
            raise InputError("Invalid cleaned spend row or Redacted leaked into supplier analysis")
        row["day"] = date.fromisoformat(row["pay_date"])
    return rows


def public_row(row: dict) -> dict:
    return {k: v for k, v in row.items() if k != "day"}


def tag_summary(rows: list[dict], amount_field: str = "amount_pence", tag_field: str = "tag") -> dict:
    result = {}
    for tag in TAGS:
        subset = [r for r in rows if r.get(tag_field) == tag]
        result[tag] = {"rows": len(subset), "amount_pence": sum(int(r[amount_field]) for r in subset),
                       "gbp": gbp(sum(int(r[amount_field]) for r in subset)), "suppliers": len({r["supplier_norm"] for r in subset})}
    return result


def supplier_totals(rows: list[dict], months: int) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[row["supplier_norm"]].append(row)
    result = []
    for supplier, members in sorted(groups.items()):
        by_tag, by_name = Counter(), Counter()
        for r in members:
            by_tag[r["tag"]] += r["amount_pence"]
            by_name[r["Supplier name"]] += r["amount_pence"]
        total = sum(r["amount_pence"] for r in members)
        dominant = sorted(by_tag, key=lambda k: (-by_tag[k], k))[0]
        result.append({"supplier_norm": supplier, "supplier": sorted(by_name, key=lambda k: (-by_name[k], k))[0],
                       "company_number": next((r.get("company_number") for r in members if r.get("company_number")), ""),
                       "amount_pence": total, "total_gbp": gbp(total), "annualised_estimate_pence": annualised_pence(total, months),
                       "annualised_estimate_gbp": gbp(annualised_pence(total, months)), "estimate_label": "annualised estimate",
                       "dominant_tag": dominant, "multi_tag": len(by_tag) > 1, "tag_totals_gbp": {k: gbp(v) for k, v in sorted(by_tag.items())},
                       "n_payments": len(members), "narratives": sorted({r["Narrative"] for r in members}),
                       "services": sorted({r["Service"] for r in members}), "row_ids": [r["row_id"] for r in sorted(members, key=lambda r: r["row_id"])]})
    return sorted(result, key=lambda r: (-r["amount_pence"], r["supplier_norm"]))


def distinctive(name: str) -> set[str]:
    return {t for t in name.split() if len(t) >= 3 and t not in GENERIC}


def match_supplier(name: str, company: str, active: list[dict], spend_names: set[str]) -> dict:
    exact = [n for n in active if n["supplier_norm"] == name or (company and company == n.get("company_number"))]
    if exact:
        return {"match_class": "exact", "candidate": sorted({r["supplier_norm"] for r in exact}),
                "match_rule": "company_number" if company and any(company == n.get("company_number") for n in exact) else "normalised_name",
                "notice_ids": sorted({r.get("notice_id", r["row_id"]) for r in exact}), "source": sorted({r["source"] for r in exact})}
    names = sorted({n["supplier_norm"] for n in active})
    ratios = [(SequenceMatcher(None, name, n).ratio(), n) for n in names]
    ratios.sort(key=lambda x: (-x[0], x[1]))
    if ratios and ratios[0][0] >= 0.85:
        return {"match_class": "near_ratio", "candidate": [ratios[0][1]], "match_rule": "SequenceMatcher >= 0.85",
                "similarity": round(ratios[0][0], 6), "notice_ids": sorted({r.get("notice_id", r["row_id"]) for r in active if r["supplier_norm"] == ratios[0][1]})}
    spend_frequency = Counter(t for n in spend_names for t in distinctive(n))
    notice_frequency = Counter(t for n in names for t in distinctive(n))
    a = distinctive(name)
    candidates = []
    for candidate in names:
        b = distinctive(candidate)
        smaller, larger = (a, b) if len(a) <= len(b) else (b, a)
        if smaller and smaller <= larger and (len(smaller) >= 2 or all(spend_frequency[t] == 1 and notice_frequency[t] == 1 for t in smaller)):
            candidates.append(candidate)
    if candidates:
        return {"match_class": "near_contain", "candidate": candidates, "match_rule": "distinctive token subset with uniqueness guard",
                "notice_ids": sorted({r.get("notice_id", r["row_id"]) for r in active if r["supplier_norm"] in candidates})}
    return {"match_class": "none", "candidate": [], "match_rule": "none", "notice_ids": []}


def threshold_clustering(rows: list[dict], thresholds: list[dict], full: Path) -> dict:
    tiers, flags = [], []
    for threshold in thresholds:
        t, trigger = threshold["amount_pence"], threshold["effective_trigger_pence"]
        band = [r for r in rows if r["amount_pence"] * 10 >= t * 9 and r["amount_pence"] < trigger]
        comparator = [r for r in rows if trigger <= r["amount_pence"] and r["amount_pence"] * 10 < t * 11]
        baseline = [r for r in rows if r["amount_pence"] * 2 >= t and r["amount_pence"] * 2 < t * 3]
        counts = Counter(r["supplier_norm"] for r in band)
        record = {"threshold": threshold["value"], "inclusive": threshold["inclusive"], "rule_ids": threshold["rule_ids"], "count": len(band),
                  "amount_pence": sum(r["amount_pence"] for r in band), "gbp": gbp(sum(r["amount_pence"] for r in band)),
                  "comparator": {"count": len(comparator), "gbp": gbp(sum(r["amount_pence"] for r in comparator))},
                  "baseline": {"count": len(baseline), "gbp": gbp(sum(r["amount_pence"] for r in baseline))},
                  "supplier_concentration": [{"supplier_norm": s, "count": n} for s, n in counts.most_common(20)], "by_tag": tag_summary(band),
                  "top20": [public_row(r) for r in sorted(band, key=lambda r: (-r["amount_pence"], r["row_id"]))[:20]]}
        tiers.append(record)
        flags.extend({**public_row(row), "threshold": threshold["value"], "threshold_pence": t} for row in band)
    write_csv(full / "threshold-clustering.csv", flags)
    unique = {r["row_id"]: r for r in flags}
    return {"parameters": {"band": "[0.9T, T), upper boundary includes T only when rule trigger is exclusive", "comparator": "[T,1.1T)", "baseline": "[0.5T,1.5T)"},
            "rule_ids": sorted({rid for t in thresholds for rid in t["rule_ids"]}), "count": len(unique), "gbp": gbp(sum(r["amount_pence"] for r in unique.values())),
            "count_definition": "distinct payments flagged at one or more thresholds", "tiers": tiers, "full_file": str(full / "threshold-clustering.csv")}


def select_disjoint_windows(candidates: list[dict]) -> list[dict]:
    """Highest total first; retain non-overlapping source row sets deterministically."""
    chosen, used = [], set()
    for candidate in sorted(candidates, key=lambda r: (-r["amount_pence"], r["window_start"], r["row_ids"])):
        if not used.intersection(candidate["row_ids"]):
            chosen.append(candidate)
            used.update(candidate["row_ids"])
    return chosen


def window_record(members: list[dict], prefix: str, extra: str = "") -> dict:
    tag_total = Counter()
    for row in members:
        tag_total[row["tag"]] += row["amount_pence"]
    ids = [r["row_id"] for r in members]
    amount = sum(r["amount_pence"] for r in members)
    return {"group_id": stable_id(prefix, [extra, *sorted(ids)]), "supplier_norm": members[0]["supplier_norm"], "supplier": members[0]["Supplier name"],
            "window_start": min(r["pay_date"] for r in members), "window_end": max(r["pay_date"] for r in members), "n_payments": len(members),
            "amount_pence": amount, "total_gbp": gbp(amount), "distinct_amounts": len({r["amount_pence"] for r in members}),
            "services": sorted({r["Service"] for r in members}), "tag": sorted(tag_total, key=lambda k: (-tag_total[k], k))[0],
            "multi_tag": len(tag_total) > 1, "tag_totals_gbp": {k: gbp(v) for k, v in tag_total.items()}, "row_ids": ids}


def split_purchases(rows: list[dict], thresholds: list[dict], full: Path) -> dict:
    groups = defaultdict(list)
    for row in rows:
        groups[row["supplier_norm"]].append(row)
    tiers, flags = [], []
    for threshold in [t for t in thresholds if t["competition_triggering"]]:
        candidates = []
        trigger = threshold["effective_trigger_pence"]
        for supplier, members in sorted(groups.items()):
            eligible = sorted([r for r in members if r["amount_pence"] < trigger], key=lambda r: (r["pay_date"], r["row_id"]))
            supplier_windows, seen = [], set()
            for row in eligible:
                # Anchoring by day includes every payment on the first day.
                if row["pay_date"] in seen:
                    continue
                seen.add(row["pay_date"])
                window = [r for r in eligible if row["day"] <= r["day"] < row["day"] + timedelta(days=30)]
                if len(window) >= 2 and sum(r["amount_pence"] for r in window) >= trigger:
                    item = window_record(window, "SPLIT", str(threshold["amount_pence"]))
                    item.update({"threshold": threshold["value"], "threshold_pence": threshold["amount_pence"], "effective_trigger_pence": trigger,
                                 "window_id": item["group_id"], "rule_ids": threshold["rule_ids"]})
                    supplier_windows.append(item)
            candidates.extend(select_disjoint_windows(supplier_windows))
        candidates.sort(key=lambda r: (-r["amount_pence"], r["group_id"]))
        flags.extend(candidates)
        general = [r for r in candidates if r["tag"] == "general_procurement"]
        placements = [r for r in candidates if r["tag"] == "care_or_education_placement"]
        tiers.append({"threshold": threshold["value"], "rule_ids": threshold["rule_ids"], "windows": len(candidates), "suppliers": len({r["supplier_norm"] for r in candidates}),
                      "gbp": gbp(sum(r["amount_pence"] for r in candidates)), "by_tag": tag_summary(candidates),
                      "headline": {"windows": len(general), "gbp": gbp(sum(r["amount_pence"] for r in general))},
                      "placements": {"windows": len(placements), "gbp": gbp(sum(r["amount_pence"] for r in placements)), "caveat": "Periodic care/education fees can legitimately recur."}, "top20": candidates[:20]})
    write_csv(full / "split-purchases.csv", flags)
    return {"parameters": {"window_days": 30, "interval": "[anchor calendar date, anchor + 30 days)", "deduplication": "per supplier per threshold, highest total first, discard overlapping row sets",
                           "headline_tag": "general_procurement"}, "rule_ids": sorted({rid for t in thresholds if t["competition_triggering"] for rid in t["rule_ids"]}),
            "count": sum(t["headline"]["windows"] for t in tiers), "count_definition": "general-procurement windows summed across thresholds; may share payments across thresholds",
            "gbp": gbp(sum(r["amount_pence"] for r in flags if r["tag"] == "general_procurement")), "tiers": tiers, "full_file": str(full / "split-purchases.csv")}


def high_value_suppliers(suppliers: list[dict], thresholds: list[dict], months: int, full: Path) -> tuple[dict, list[dict]]:
    competition = [t for t in thresholds if t["competition_triggering"]]
    if not competition:
        write_csv(full / "high-value-suppliers.csv", [])
        return {"skipped": True, "reason": "No numeric competition-triggering threshold is available"}, []
    lowest = min(competition, key=lambda t: t["amount_pence"])
    # Compare unrounded annualised estimate to the trigger.
    selected = [s for s in suppliers if s["amount_pence"] * 12 >= lowest["effective_trigger_pence"] * months]
    write_csv(full / "high-value-suppliers.csv", selected)
    general = [r for r in selected if r["dominant_tag"] == "general_procurement"]
    statutory = []
    for t in competition:
        if t["parameter_refs"]:
            sub = [s for s in suppliers if s["amount_pence"] * 12 >= t["effective_trigger_pence"] * months]
            statutory.append({"threshold": t["value"], "parameters": t["parameter_refs"], "count": len(sub), "gbp": gbp(sum(s["amount_pence"] for s in sub)), "top20": sub[:20]})
    return {"parameters": {"threshold": lowest["value"], "inclusive": lowest["inclusive"], "annualisation": "total × (12 / distinct months covered)", "annualised_label": "annualised estimate"},
            "rule_ids": lowest["rule_ids"], "count": len(selected), "gbp": gbp(sum(r["amount_pence"] for r in selected)),
            "headline": {"count": len(general), "gbp": gbp(sum(r["amount_pence"] for r in general)), "top20": general[:20]},
            "by_tag": tag_summary(selected, tag_field="dominant_tag"), "tag_tables": {tag: [s for s in selected if s["dominant_tag"] == tag][:20] for tag in TAGS},
            "statutory_tiers": statutory, "top20": selected[:20], "full_file": str(full / "high-value-suppliers.csv")}, selected


def duplicate_groups(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for r in rows:
        groups[(r["supplier_norm"], r["amount_pence"])].append(r)
    selected = []
    for (supplier, amount), members in sorted(groups.items()):
        candidates, seen = [], set()
        for row in sorted(members, key=lambda r: (r["pay_date"], r["row_id"])):
            if row["pay_date"] in seen:
                continue
            seen.add(row["pay_date"])
            window = sorted([r for r in members if row["day"] <= r["day"] <= row["day"] + timedelta(days=7)], key=lambda r: (r["Date"], r["row_id"]))
            if len(window) < 2:
                continue
            record = window_record(window, "DUP")
            record.update({"tier": "same_timestamp" if len({r["Date"] for r in window}) == 1 else "different_time",
                           "payment_amount_pence": amount, "payment_amount_gbp": gbp(amount), "excess_pence": amount * (len(window) - 1),
                           "excess_gbp": gbp(amount * (len(window) - 1))})
            candidates.append(record)
        selected.extend(select_disjoint_windows(candidates))
    return sorted(selected, key=lambda r: (-r["excess_pence"], r["group_id"]))


def duplicates(rows: list[dict], full: Path) -> dict:
    groups = duplicate_groups(rows)
    write_csv(full / "duplicates.csv", groups)
    tiers = {}
    for tier in ("same_timestamp", "different_time"):
        subset = [r for r in groups if r["tier"] == tier]
        tiers[tier] = {"groups": len(subset), "rows": sum(r["n_payments"] for r in subset), "gbp_beyond_first": gbp(sum(r["excess_pence"] for r in subset)),
                       "by_tag": tag_summary(subset, "excess_pence"), "top20": subset[:20]}
    return {"parameters": {"window_days": 7, "date_rule": "calendar difference <= 7 days", "comparison": "same normalised supplier and exact integer pence",
                           "tier_rule": "Group with any differing timestamp is different_time; otherwise same_timestamp. Groups are disjoint, highest total first."},
            "rule_ids": [], "count": len(groups), "rows": sum(r["n_payments"] for r in groups), "gbp": gbp(sum(r["excess_pence"] for r in groups)),
            "amount_definition": "value beyond the first instance; potential duplicate indicator, not confirmed duplicate", "tiers": tiers, "top20": groups[:20], "full_file": str(full / "duplicates.csv")}


def off_contract(suppliers: list[dict], matches: dict, rules: dict, months: int, contracts: dict, full: Path) -> dict:
    write_csv(full / "off-contract.csv", [])
    write_csv(full / "off-contract-unmatched.csv", [])
    if not (contracts["contracts_present"] or contracts["register_present"]):
        return {"skipped": True, "reason": "no usable contracts.csv or contract register in data/", "caveat": NOTICE_CAVEAT}
    threshold = publication_threshold(rules)
    if threshold is None:
        return {"skipped": True, "reason": "No numeric publication threshold could be derived from rules.json; no smaller supplier is classed", "caveat": NOTICE_CAVEAT}
    trigger = threshold["amount_pence"] + (0 if threshold["inclusive"] else 1)
    selected = [{**s, **matches[s["supplier_norm"]]} for s in suppliers if s["amount_pence"] * 12 >= trigger * months]
    unmatched = [s for s in selected if s["match_class"] != "exact"]
    headline = [s for s in unmatched if s["dominant_tag"] == "general_procurement"]
    write_csv(full / "off-contract.csv", selected)
    write_csv(full / "off-contract-unmatched.csv", unmatched)
    return {"parameters": {"publication_threshold": threshold["value"], "inclusive": threshold["inclusive"], "near_matches_count_as_matches": False, "annualised_label": "annualised estimate"},
            "rule_ids": threshold["rule_ids"], "contracts_present": contracts["contracts_present"], "register_present": contracts["register_present"],
            "count": len(unmatched), "gbp": gbp(sum(s["amount_pence"] for s in unmatched)), "eligible_suppliers": len(selected),
            "by_match_class": {kind: {"count": len([s for s in selected if s["match_class"] == kind]), "gbp": gbp(sum(s["amount_pence"] for s in selected if s["match_class"] == kind))} for kind in ("exact", "near_ratio", "near_contain", "none")},
            "unmatched_by_tag": tag_summary(unmatched, tag_field="dominant_tag"), "headline": {"count": len(headline), "gbp": gbp(sum(s["amount_pence"] for s in headline)), "top20": headline[:20]},
            "top20": unmatched[:20], "caveat": NOTICE_CAVEAT, "near_match_caveat": "Near matches are candidates for auditor confirmation and remain unmatched in counts.",
            "scope_caveat": "Only suppliers whose annualised estimate reaches the publication threshold are classed. Smaller suppliers are outside this test.", "full_file": str(full / "off-contract.csv")}


def expired_notice_spend(suppliers: list[dict], notices: list[dict], contracts: dict, rules: dict, full: Path, window_start: str) -> dict:
    write_csv(full / "expired-notice-spend.csv", [])
    if not contracts["contracts_present"]:
        return {"skipped": True, "reason": "usable contracts.csv is required"}
    result = []
    for supplier in suppliers:
        matched = [n for n in notices if n["supplier_norm"] == supplier["supplier_norm"] or (supplier["company_number"] and supplier["company_number"] == n.get("company_number"))]
        if matched and all(n["contract_end"] and n["contract_end"] < window_start for n in matched):
            result.append({**supplier, "latest_end_date": max(n["contract_end"] for n in matched), "notice_ids": sorted({n["notice_id"] for n in matched})})
    write_csv(full / "expired-notice-spend.csv", result)
    return {"parameters": {"window_start": window_start, "match": "exact only; every matching notice must have ended before window start"},
            "rule_ids": rule_ids_for(rules, "App C row D"), "count": len(result), "gbp": gbp(sum(s["amount_pence"] for s in result)),
            "annualised_estimate_gbp": gbp(sum(s["annualised_estimate_pence"] for s in result)), "top20": result[:20],
            "caveat": "Indicator for checking extension approvals. A newer contract may exist without a matching published notice. " + NOTICE_CAVEAT,
            "full_file": str(full / "expired-notice-spend.csv")}


def spend_vs_award(suppliers: list[dict], notices: list[dict], contracts: dict, rules: dict, months: int, full: Path) -> dict:
    write_csv(full / "spend-vs-award.csv", [])
    if not contracts["contracts_present"]:
        return {"skipped": True, "reason": "usable contracts.csv is required"}
    result, excluded = [], Counter()
    active = [n for n in notices if is_true(n["active"]) and not is_true(n["starts_after_window"])]
    for supplier in suppliers:
        matched = [n for n in active if n["supplier_norm"] == supplier["supplier_norm"] or (supplier["company_number"] and supplier["company_number"] == n.get("company_number"))]
        unique = {n["notice_id"]: n for n in matched}
        if len(unique) != 1:
            excluded["no_unique_active_notice"] += 1
            continue
        notice = next(iter(unique.values()))
        if int(notice["suppliers_on_notice"]) != 1:
            excluded["multi_supplier_award"] += 1
            continue
        award = int(notice["award_pence"])
        if award <= 0:
            excluded["zero_value_award"] += 1
            continue
        if not notice["contract_start"] or not notice["contract_end"]:
            excluded["missing_duration"] += 1
            continue
        days = (date.fromisoformat(notice["contract_end"]) - date.fromisoformat(notice["contract_start"])).days + 1
        if days <= 0:
            excluded["invalid_duration"] += 1
            continue
        years = Decimal(days) / Decimal("365.25")
        annual_estimate = Decimal(supplier["amount_pence"]) * 12 / months
        annual_award = Decimal(award) / years
        ratio = annual_estimate / annual_award
        if ratio < Decimal("1.25"):
            continue
        result.append({**supplier, "notice_id": notice["notice_id"], "contract_start": notice["contract_start"], "contract_end": notice["contract_end"],
                       "contract_days": days, "contract_years": float(years), "awarded_value_gbp": gbp(award), "award_pence": award,
                       "award_annual_rate_gbp": float((annual_award / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)), "ratio": float(ratio.quantize(Decimal("0.000001")))})
    result.sort(key=lambda r: (-r["ratio"], r["supplier_norm"]))
    write_csv(full / "spend-vs-award.csv", result)
    return {"parameters": {"ratio_min": 1.25, "contract_years": "(end date - start date + 1 inclusive day) / 365.25", "annualised_label": "annualised estimate",
                           "eligibility": "exactly one active notice, one supplier on that notice, positive award, complete valid duration"},
            "rule_ids": rule_ids_for(rules, "App C row E"), "count": len(result), "gbp": gbp(sum(r["amount_pence"] for r in result)), "excluded": dict(excluded),
            "top20": result[:20], "caveat": "Indicator of spend beyond a whole-term award annual rate; award values may be estimates or maxima. Verify variations and contract scope before conclusions.",
            "full_file": str(full / "spend-vs-award.csv")}


def analyse(data: Path, full: Path, output: Path, rules_path: Path) -> dict:
    rules, thresholds, skipped = load_rules(rules_path)
    log_path = full / "cleaning-log.json"
    if not log_path.exists():
        raise InputError("Run scripts/clean.py before scripts/analyse.py")
    log = json.loads(log_path.read_text())
    rows = restore_spend(read_csv(full / "spend-clean.csv"))
    if not rows:
        raise InputError("No procurement rows remain after exclusions")
    months = int(log["months_covered"])
    if months <= 0:
        raise InputError("months_covered must be positive")
    notices = read_csv(full / "notices-clean.csv")
    register = read_csv(full / "register-clean.csv")
    contracts = log["contracts"]
    suppliers = supplier_totals(rows, months)
    active = [n for n in notices if is_true(n["active"]) and not is_true(n["starts_after_window"])] if contracts["contracts_present"] else []
    active += [r for r in register if is_true(r["active"])]
    spend_names = {s["supplier_norm"] for s in suppliers}
    matches = {s["supplier_norm"]: match_supplier(s["supplier_norm"], s["company_number"], active, spend_names) for s in suppliers} if active else {s["supplier_norm"]: {"match_class": "none", "candidate": [], "match_rule": "no active source", "notice_ids": []} for s in suppliers}
    match_rows = [{"supplier_norm": s["supplier_norm"], "supplier": s["supplier"], "row_ids": s["row_ids"], **matches[s["supplier_norm"]]} for s in suppliers]
    write_csv(full / "supplier-match.csv", match_rows)
    write_csv(full / "near-matches.csv", [r for r in match_rows if r["match_class"].startswith("near_")])
    write_csv(full / "supplier-totals.csv", suppliers)
    high_value, selected = high_value_suppliers(suppliers, thresholds, months, full)
    tests = {
        "threshold_clustering": threshold_clustering(rows, thresholds, full),
        "split_purchases": split_purchases(rows, thresholds, full),
        "high_value_suppliers": high_value,
        "duplicates": duplicates(rows, full),
        "off_contract": off_contract(suppliers, matches, rules, months, contracts, full),
        "expired_notice_spend": expired_notice_spend(suppliers, notices, contracts, rules, full, log["date_min"]),
        "spend_vs_award": spend_vs_award(suppliers, notices, contracts, rules, months, full),
    }
    for name, test in tests.items():
        if test.get("skipped"):
            skipped.append({"test": name, "reason": test["reason"]})
    for name, parameter in rules.get("parameters", {}).items():
        if "STATUTORY" in name and (parameter.get("value") if isinstance(parameter, dict) else parameter) is None:
            for test in ("high_value_suppliers", "off_contract"):
                skipped.append({"test": test, "tier": name, "reason": f"{name} is null"})
    payload = {
        "generated_at": date.today().isoformat(), "schema_version": "1.0", "scripts": ["scripts/clean.py", "scripts/analyse.py"],
        "execution": {"producer": "Codex preparation", "claude_code_verified": False, "human_approval": "pending", "source_rules_sha256": hashlib.sha256(rules_path.read_bytes()).hexdigest()},
        "population": {k: log[k] for k in ("files", "rows_raw", "rows_after_exclusions", "date_min", "date_max", "months_covered", "excluded")},
        "thresholds": thresholds, "skipped": skipped, "contracts": contracts,
        "matching": {**dict(Counter(m["match_class"] for m in matches.values())), "near_matches_file": str(full / "near-matches.csv"), "near_matches_require_human_confirmation": True},
        "tests": tests,
    }
    payload["population"].update({"annualisation_factor": float(Decimal(12) / months), "total_pence": sum(r["amount_pence"] for r in rows),
                                  "total_gbp": gbp(sum(r["amount_pence"] for r in rows)), "tags": tag_summary(rows),
                                  "limitations": ["population is expenditure over £500 only; split and duplicate indicators are lower bounds", "Date is a payment-run timestamp, not an invoice date",
                                                  "annualised estimate assumes observed months are representative", "mixed procurement categories cannot be assigned statutory tiers without fieldwork", "indicators to investigate; not findings of wrongdoing"],
                                  "warnings": log["warnings"]})
    write_json(output, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--full", type=Path, default=Path("outputs/analytics-full"))
    parser.add_argument("--output", type=Path, default=Path("outputs/analytics.json"))
    parser.add_argument("--rules", type=Path, default=Path("outputs/rules.json"))
    args = parser.parse_args()
    try:
        result = analyse(args.data, args.full, args.output, args.rules)
    except (InputError, ValueError, KeyError, OSError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"population_rows": result["population"]["rows_after_exclusions"], "tests": {k: {"count": v.get("count"), "skipped": v.get("skipped", False)} for k, v in result["tests"].items()}, "skipped_tiers": len(result["skipped"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
