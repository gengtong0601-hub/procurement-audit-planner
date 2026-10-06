#!/usr/bin/env python3
"""Read-only input cleaning for the guide's procurement indicators.

Currency is stored as integer pence; CSV Net amount is a presentation field.
No format inference, supplier-level use of Redacted, or silent bad-row repair.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

import pandas as pd

EXPECTED = ["Service", "Expenditure category", "Narrative", "Date", "Net amount", "Supplier name"]
DROP_TOKENS = {"LTD", "LIMITED", "PLC", "LLP", "LLC", "INC", "CIC", "CIO", "UK", "THE"}
BUYERS = {"West Berkshire Council", "West Berkshire"}
PENSION_RE = r"LGPS|PENSION|SUPERANNUATION"
AUTHORITY_RE = r"\b(COUNCIL|BOROUGH|COUNTY|CNCL|NHS|POLICE|FIRE AUTHORITY|FIRE AND RESCUE|HMRC|HM REVENUE|DEPARTMENT FOR|MINISTRY OF)\b"
TAG_RULES = {
    "care_or_education_placement": "Service ^(Adult Social Care|Children's Social Care|Education); Narrative ^(Private Contractors|Other agencies|Voluntary Associations)$",
    "grant": "Narrative GRANT",
    "agency_staff": "Narrative AGENCY",
    "premises_non_procurement": "Narrative RENT|RATES|WATER RATES|LEASE",
    "general_procurement": "otherwise; first match wins",
}
NOTICE_CAVEAT = (
    'contracts.csv holds published *notices*, not a contract register. It holds '
    'awards published on Contracts Finder in roughly the last five years. A '
    'contract awarded earlier (e.g. long-running waste or highways contracts), '
    'one advertised only on Find a Tender, a framework call-off recorded under '
    'another buyer, or an exempt placement will have no notice here. "No '
    'notice found" is therefore an indicator to check against the council\'s '
    'contract register, never evidence of off-contract spend.'
)


class InputError(ValueError):
    """Invalid inputs must be corrected at source, never guessed."""


def is_council_buyer(name: str) -> bool:
    """Identity allow-list tolerates case/spacing only, never substrings or fuzzy names."""
    normalised = " ".join(str(name).split()).casefold()
    return normalised in {buyer.casefold() for buyer in BUYERS}


def normalise_supplier(name: str) -> str:
    text = str(name).upper().replace("&", " AND ")
    text = re.sub(r"\([^)]*\)|\[[^]]*\]", " ", text)
    text = re.split(r"\bT\s*/\s*A\b|\bTRADING\s+AS\b", text, maxsplit=1)[0]
    return " ".join(t for t in re.sub(r"[^A-Z0-9 ]", " ", text).split() if t not in DROP_TOKENS)


def to_pence(value, context: str = "amount") -> int:
    if pd.isna(value) or str(value).strip() == "":
        raise InputError(f"{context}: missing amount")
    try:
        number = Decimal(str(value).replace(",", "").replace("£", "").strip())
    except InvalidOperation as exc:
        raise InputError(f"{context}: invalid amount {value!r}") from exc
    if not number.is_finite():
        raise InputError(f"{context}: non-finite amount")
    pennies = number * 100
    # Excel binary floats may expose sub-penny rounding noise, not extra money.
    rounded = pennies.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    if abs(pennies - rounded) > Decimal("0.000001"):
        raise InputError(f"{context}: amount has more than two decimal places {value!r}")
    return int(rounded)


def gbp(pence: int) -> float:
    return float(Decimal(int(pence)) / 100)


def money_string(pence: int) -> str:
    return f"{Decimal(int(pence)) / 100:.2f}"


def parse_spend_date(value, context: str = "spend date") -> datetime:
    if pd.isna(value):
        raise InputError(f"{context}: missing date")
    if isinstance(value, datetime):
        return value.to_pydatetime() if hasattr(value, "to_pydatetime") else value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    # Explicit US formats only; no pd.to_datetime format inference.
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%m/%d/%Y %H:%M:%S.%f", "%m/%d/%Y %H:%M:%S", "%m/%d/%y %H:%M:%S"):
        try:
            return datetime.strptime(str(value).strip(), fmt)
        except ValueError:
            pass
    raise InputError(f"{context}: expected M/D/Y text or Excel datetime, got {value!r}")


def parse_notice_date(value: str, context: str = "notice date") -> str:
    if not str(value).strip():
        return ""
    try:
        return datetime.strptime(str(value).strip(), "%d/%m/%Y").date().isoformat()
    except ValueError as exc:
        raise InputError(f"{context}: expected D/M/Y, got {value!r}") from exc


def parse_published(value: str, context: str) -> str:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError as exc:
        raise InputError(f"{context}: invalid ISO Published Date {value!r}") from exc


def tag_spend(row: dict) -> str:
    service, narrative = row["Service"], row["Narrative"]
    if re.search(r"^(Adult Social Care|Children's Social Care|Education)", service, re.I) and re.fullmatch(r"Private Contractors|Other agencies|Voluntary Associations", narrative, re.I):
        return "care_or_education_placement"
    for tag, pattern in (("grant", r"GRANT"), ("agency_staff", r"AGENCY"), ("premises_non_procurement", r"RENT|RATES|WATER RATES|LEASE")):
        if re.search(pattern, narrative, re.I):
            return tag
    return "general_procurement"


def exclusion_for(row: dict) -> str:
    if row["Supplier name"].strip().casefold() == "redacted":
        return "redacted_supplier"
    if re.search(PENSION_RE, row["Narrative"], re.I):
        return "pension_statutory"
    if (re.search(AUTHORITY_RE, row["Supplier name"], re.I) or re.search("JOINT ARRANGEMENTS", row["Narrative"], re.I)) and row["Narrative"].strip().casefold() != "private contractors":
        return "inter_authority"
    return ""


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or list(dict.fromkeys(k for row in rows for k in row))
    if not fields:
        fields = ["row_id"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ";".join(map(str, v)) if isinstance(v, list) else v for k, v in row.items()})


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def load_spend(data: Path) -> tuple[list[dict], list[dict], dict]:
    paths = sorted([*data.joinpath("spend").glob("*.xlsx"), *data.joinpath("spend").glob("*.csv")])
    if not paths:
        raise InputError(f"No spend workbooks or CSVs in {data / 'spend'}")
    kept, excluded, profiles = [], [], []
    all_dates = []
    for path in paths:
        raw = pd.read_excel(path, sheet_name="Data to publish", header=None) if path.suffix == ".xlsx" else pd.read_csv(path, header=None)
        headers = [int(i) for i in raw.index if str(raw.iloc[i, 0]).strip() == "Service"]
        if len(headers) != 1:
            raise InputError(f"{path.name}: expected exactly one Service header row; found {headers}")
        header = headers[0]
        columns = [str(v).strip() for v in raw.iloc[header].tolist()]
        if columns != EXPECTED:
            raise InputError(f"{path.name}: columns do not match guide. Expected {EXPECTED}; found {columns}")
        frame = raw.iloc[header + 1:].copy()
        frame.columns = columns
        if frame.isna().all(axis=1).any():
            raise InputError(f"{path.name}: blank data rows present; source review required")
        n = 0
        for sheet_index, source in frame.iterrows():
            row_id = f"{path.name}:{int(sheet_index) + 1}"
            if pd.isna(source["Supplier name"]) or not str(source["Supplier name"]).strip():
                raise InputError(f"{row_id}: missing supplier")
            timestamp = parse_spend_date(source["Date"], row_id)
            amount = to_pence(source["Net amount"], row_id)
            if amount < 0:
                raise InputError(f"{row_id}: negative amount {money_string(amount)}; stopped for source review")
            row = {col: "" if pd.isna(source[col]) else str(source[col]).strip() for col in EXPECTED}
            row.update({"Date": timestamp.isoformat(timespec="milliseconds"), "Net amount": money_string(amount), "source_file": path.name,
                        "source_sheet": "Data to publish" if path.suffix == ".xlsx" else "CSV", "source_row": int(sheet_index) + 1,
                        "row_id": row_id, "pay_date": timestamp.date().isoformat(), "amount_pence": amount,
                        "supplier_norm": normalise_supplier(row["Supplier name"]), "company_number": ""})
            if not row["supplier_norm"]:
                raise InputError(f"{row_id}: supplier normalises to empty string")
            row["tag"] = tag_spend(row)
            row["exclusion"] = exclusion_for(row)
            (excluded if row["exclusion"] else kept).append(row)
            all_dates.append(row["pay_date"])
            n += 1
        profiles.append({"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "sheet": "Data to publish", "header_row": header + 1, "rows": n,
                         "blank_expenditure_category": int(frame["Expenditure category"].isna().sum())})
    reasons = {
        "redacted_supplier": "Redacted combines unrelated payees; excluded from supplier-level tests.",
        "pension_statutory": f"Narrative matches {PENSION_RE}; statutory pension indicator.",
        "inter_authority": "Public-body supplier or JOINT ARRANGEMENTS, except Private Contractors narrative.",
    }
    exclusions = {}
    for kind, reason in reasons.items():
        items = [r for r in excluded if r["exclusion"] == kind]
        exclusions[kind] = {"rows": len(items), "amount_pence": sum(r["amount_pence"] for r in items), "gbp": gbp(sum(r["amount_pence"] for r in items)), "reason": reason}
    months = sorted({d[:7] for d in all_dates})
    log = {"files": profiles, "rows_raw": len(kept) + len(excluded), "rows_after_exclusions": len(kept),
           "raw_total_pence": sum(r["amount_pence"] for r in kept + excluded), "total_pence": sum(r["amount_pence"] for r in kept),
           "date_min": min(all_dates), "date_max": max(all_dates), "months_covered": len(months), "months": months,
           "excluded": exclusions, "tag_rules": TAG_RULES, "exclusion_regexes": {"pension": PENSION_RE, "inter_authority": AUTHORITY_RE},
           "warnings": [], "provenance": "Prepared by Codex; Claude Code agent execution and human approval pending."}
    if len(months) != (int(max(months)[:4]) - int(min(months)[:4])) * 12 + int(max(months)[5:]) - int(min(months)[5:]) + 1:
        log["warnings"].append("Spend calendar months have gaps; annualisation is an estimate based on distinct observed months.")
    return kept, excluded, log


def unpack_suppliers(packed: str, context: str) -> list[dict]:
    if not packed.startswith("[") or not packed.endswith("]"):
        raise InputError(f"{context}: malformed packed supplier field")
    blocks = packed[1:-1].split("][")
    result = []
    for block in blocks:
        parts = block.split("|")
        if len(parts) != 6 or not parts[0].strip():
            raise InputError(f"{context}: expected six pipe-delimited supplier elements")
        name = parts[0].strip()
        result.append({"Supplier name": name, "supplier_norm": normalise_supplier(name), "company_number": parts[3].strip() if parts[2].strip() == "COMPANIES_HOUSE" else ""})
    return result


def load_notices(data: Path, start: str, end: str) -> tuple[list[dict], dict]:
    path = data / "contracts.csv"
    log = {"contracts_present": False, "register_present": False, "rows_in_file": 0, "rows_for_council": 0,
           "notice_supplier_pairs": 0, "distinct_suppliers": 0, "active_in_window": 0, "ended_before_window": 0,
           "zero_value_awards": 0, "rows_per_year": {}, "published_range": [], "warnings": [], "caveat": NOTICE_CAVEAT}
    if not path.exists():
        log["absent_reason"] = "no contracts.csv in data/"
        return [], log
    raw = read_csv(path)
    log["rows_in_file"] = len(raw)
    if not raw:
        log["absent_reason"] = "contracts.csv is empty"
        return [], log
    supplier_column = next((key for key in raw[0] if key == "Supplier" or key.startswith("Supplier [")), None)
    required = {"Organisation Name", "Notice Identifier", "Title", "Contract start date", "Contract end date", "Awarded Date", "Published Date", "Awarded Value", "OJEU Procedure Type"}
    if required - raw[0].keys() or not supplier_column:
        raise InputError(f"contracts.csv: missing expected columns: {sorted(required - raw[0].keys())}; supplier column found={bool(supplier_column)}")
    council = [(i + 2, r) for i, r in enumerate(raw) if is_council_buyer(r["Organisation Name"])]
    log["rows_for_council"] = len(council)
    log["rows_dropped_other_buyers"] = len(raw) - len(council)
    log["dropped_buyers"] = dict(Counter(r["Organisation Name"] for r in raw if not is_council_buyer(r["Organisation Name"])))
    log["organisations_kept"] = sorted({r["Organisation Name"] for _, r in council})
    normalised_variants = sum(1 for _, r in council if r["Organisation Name"] not in BUYERS)
    log["normalised_buyer_variants_kept"] = normalised_variants
    log["buyer_matching"] = {"allowed_identities": sorted(BUYERS), "normalisation": "strip and collapse whitespace, then casefold", "comparison": "exact identity only; no substring or fuzzy matching",
                             "guide_interpretation": "Case and whitespace are spelling variants of the two named council identities. This includes the uppercase spelling shown in the guide Setup replay."}
    log["contracts_present"] = len(council) >= 20
    if not log["contracts_present"]:
        log["absent_reason"] = "fewer than 20 notices remain after the normalised exact council-identity filter; treat notice source as absent"
        log["warnings"].append(log["absent_reason"])
    pairs, years, dates, seen = [], Counter(), [], set()
    for csv_row, source in council:
        notice = source["Notice Identifier"]
        if not notice or notice in seen:
            raise InputError(f"contracts.csv:{csv_row}: empty or duplicate Notice Identifier {notice!r}")
        seen.add(notice)
        published = parse_published(source["Published Date"], f"contracts.csv:{csv_row}")
        dates.append(published[:10]); years[published[:4]] += 1
        begin = parse_notice_date(source["Contract start date"], notice)
        finish = parse_notice_date(source["Contract end date"], notice)
        awarded = parse_notice_date(source["Awarded Date"], notice)
        if begin and finish and finish < begin:
            raise InputError(f"{notice}: contract ends before start")
        award = to_pence(source["Awarded Value"], notice)
        if award < 0:
            raise InputError(f"{notice}: negative award")
        suppliers = unpack_suppliers(source[supplier_column], notice)
        active = not finish or finish >= start
        log["active_in_window" if active else "ended_before_window"] += 1
        log["zero_value_awards"] += award == 0
        for supplier in suppliers:
            pairs.append({**supplier, "notice_id": notice, "Notice Identifier": notice, "Title": source["Title"], "source_row": csv_row,
                          "source": "contracts.csv", "row_id": f"contracts.csv:{csv_row}", "contract_start": begin, "contract_end": finish,
                          "award_date": awarded, "published_date": published, "award_pence": award, "Awarded Value": money_string(award),
                          "OJEU Procedure Type": source["OJEU Procedure Type"], "suppliers_on_notice": len(suppliers),
                          "active": active, "ended_before_window": not active, "starts_after_window": bool(begin and begin > end)})
    log.update({"notice_supplier_pairs": len(pairs), "distinct_suppliers": len({r['supplier_norm'] for r in pairs}), "rows_per_year": dict(sorted(years.items())),
                "published_range": [min(dates), max(dates)] if dates else [], "active_definition": "End date on/after spend window start, or blank end date (guide's notice-coverage proxy).",
                "starts_after_window": len({r["notice_id"] for r in pairs if r["starts_after_window"]})})
    if log["starts_after_window"]:
        log["warnings"].append("Some end-date-active notices start after the spend window. Listed for traceability; these future notices are excluded from matching and spend-vs-award.")
    if len(raw) == 1000:
        log["warnings"].append("Exactly 1,000 exported rows: source may have hit Contracts Finder export cap.")
    if years:
        all_years = range(int(min(years)), int(max(years)) + 1)
        thin = [str(y) for y in all_years if years.get(str(y), 0) < 3]
        if thin:
            log["warnings"].append(f"Publication years with fewer than 3 kept notices: {', '.join(thin)}; completeness review required. This heuristic does not establish missing notices.")
    return pairs, log


def load_register(data: Path, start: str, end: str) -> list[dict]:
    path = data / "contract-register.csv"
    if not path.exists():
        return []
    # The optional register has no supplied template. Fail visibly on unknown shape.
    rows = read_csv(path)
    columns = set(rows[0]) if rows else set()
    needed = {"supplier_name", "start_date", "end_date", "value_gbp"}
    if not needed <= columns:
        raise InputError("contract-register.csv requires explicitly mapped columns supplier_name,start_date,end_date,value_gbp; dates must be ISO YYYY-MM-DD. Document the mapping before use.")
    result = []
    for i, row in enumerate(rows, start=2):
        try:
            begin = date.fromisoformat(row["start_date"]).isoformat() if row["start_date"] else ""
            finish = date.fromisoformat(row["end_date"]).isoformat() if row["end_date"] else ""
        except ValueError as exc:
            raise InputError(f"contract-register.csv:{i}: dates must be ISO YYYY-MM-DD") from exc
        result.append({"supplier_norm": normalise_supplier(row["supplier_name"]), "Supplier name": row["supplier_name"], "company_number": row.get("company_number", ""),
                       "source": "register", "row_id": f"contract-register.csv:{i}", "active": (not finish or finish >= start) and (not begin or begin <= end),
                       "award_pence": to_pence(row["value_gbp"], f"contract-register.csv:{i}")})
    return result


def clean(data: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    try:
        kept, excluded, log = load_spend(data)
        notices, notice_log = load_notices(data, log["date_min"], log["date_max"])
        register = load_register(data, log["date_min"], log["date_max"])
        notice_log["register_present"] = (data / "contract-register.csv").exists()
        notice_log["register_rows"] = len(register)
        log["contracts"] = notice_log
        fields = EXPECTED + ["source_file", "source_sheet", "source_row", "row_id", "pay_date", "amount_pence", "supplier_norm", "company_number", "tag", "exclusion"]
        write_csv(output / "spend-clean.csv", kept, fields)
        write_csv(output / "spend-excluded.csv", excluded, fields)
        write_csv(output / "notices-clean.csv", notices)
        write_csv(output / "register-clean.csv", register)
        write_json(output / "cleaning-log.json", log)
        return log
    except (InputError, ValueError, KeyError) as exc:
        write_json(output / "cleaning-error.json", {"status": "blocked", "reason": str(exc)})
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path, default=Path("outputs/analytics-full"))
    args = parser.parse_args()
    try:
        result = clean(args.data, args.output)
    except (InputError, ValueError, KeyError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"rows_raw": result["rows_raw"], "rows_after_exclusions": result["rows_after_exclusions"], "months_covered": result["months_covered"], "contracts_present": result["contracts"]["contracts_present"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
