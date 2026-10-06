"""Edge cases that change audit populations, joins, amounts, or conclusions."""
import csv
import json
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from clean import (EXPECTED, InputError, clean, exclusion_for, is_council_buyer, load_notices, load_spend,
                   normalise_supplier, parse_notice_date, parse_spend_date, tag_spend,
                   to_pence, unpack_suppliers, write_csv)
from analyse import (duplicate_groups, expired_notice_spend, high_value_suppliers,
                     load_rules, match_supplier, off_contract, publication_threshold,
                     spend_vs_award, split_purchases, supplier_totals,
                     threshold_clustering)


def payment(identifier, amount, day="2026-05-01", supplier="ACME", time="09:00:00.000", tag="general_procurement"):
    return {"row_id": identifier, "source_file": "fixture.xlsx", "source_row": 2, "pay_date": day, "day": date.fromisoformat(day),
            "Date": f"{day}T{time}", "amount_pence": amount, "Net amount": str(amount / 100), "supplier_norm": supplier,
            "Supplier name": supplier, "Service": "Corporate", "Narrative": "Supplies", "tag": tag, "company_number": ""}


def threshold(amount=10000, inclusive=True):
    return {"value": amount / 100, "amount_pence": amount, "effective_trigger_pence": amount + (not inclusive), "inclusive": inclusive,
            "competition_triggering": True, "rule_ids": ["TEST"], "parameter_refs": []}


def notice(identifier="N1", supplier="ACME", start="2026-01-01", end="2026-12-31", award=10000, count=1, active=True):
    return {"notice_id": identifier, "supplier_norm": supplier, "company_number": "", "row_id": f"contracts.csv:{identifier}",
            "source": "contracts.csv", "contract_start": start, "contract_end": end, "award_pence": award,
            "suppliers_on_notice": count, "active": active, "starts_after_window": False}


class CleaningTests(unittest.TestCase):
    def test_supplier_normalisation_shared_and_qualifiers_removed(self):
        self.assertEqual(normalise_supplier("The Acme & Sons Ltd (CHAPS ONLY) T/A Shop"), "ACME AND SONS")
        self.assertEqual(normalise_supplier("ACME AND SONS LIMITED"), "ACME AND SONS")

    def test_explicit_conflicting_date_formats(self):
        self.assertEqual(parse_spend_date("02/03/2026").date(), date(2026, 2, 3))
        self.assertEqual(parse_notice_date("02/03/2026"), "2026-03-02")
        self.assertEqual(parse_spend_date(datetime(2026, 2, 3, 1, 2, 3, 123000)).microsecond, 123000)
        with self.assertRaises(InputError):
            parse_spend_date("30/09/2026")

    def test_penny_arithmetic_and_malformed_amount(self):
        self.assertEqual(to_pence(0.1) + to_pence(0.2), 30)
        self.assertEqual(to_pence("£1,234.56"), 123456)
        with self.assertRaises(InputError):
            to_pence("100.001")
        with self.assertRaises(InputError):
            to_pence("nan")

    def test_exclusions_are_narrow_and_grants_retained(self):
        self.assertEqual(exclusion_for({"Supplier name": "redacted", "Narrative": "Grant"}), "redacted_supplier")
        self.assertEqual(exclusion_for({"Supplier name": "County Council", "Narrative": "Private Contractors"}), "")
        self.assertEqual(exclusion_for({"Supplier name": "Charity", "Narrative": "Transfer Payment"}), "")
        self.assertEqual(exclusion_for({"Supplier name": "Provider", "Narrative": "LGPS contributions"}), "pension_statutory")
        self.assertEqual(tag_spend({"Service": "Corporate", "Narrative": "Grant"}), "grant")
        self.assertEqual(tag_spend({"Service": "Adult Social Care East", "Narrative": "Private Contractors"}), "care_or_education_placement")

    def test_header_location_row_provenance_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            (data / "spend").mkdir()
            path = data / "spend/month.csv"
            with path.open("w", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(["Preamble", "", "", "", "", ""])
                writer.writerow(EXPECTED)
                writer.writerow(["Corporate", "", "Supply", "05/02/2026", "100.01", "Acme Ltd"])
            rows, _, log = load_spend(data)
            self.assertEqual(rows[0]["row_id"], "month.csv:3")
            self.assertEqual(rows[0]["pay_date"], "2026-05-02")
            self.assertEqual(log["files"][0]["header_row"], 2)
            path.write_text(path.read_text().replace("100.01", "-100.01"))
            with self.assertRaisesRegex(InputError, "negative amount"):
                load_spend(data)

    def test_packed_multisupplier_preserves_company_identifier(self):
        parsed = unpack_suppliers("[Acme Ltd|Address|COMPANIES_HOUSE|00123456|Yes|No][Beta LLP|Address|NONE||No|Yes]", "test")
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["company_number"], "00123456")
        self.assertEqual(parsed[1]["supplier_norm"], "BETA")
        with self.assertRaises(InputError):
            unpack_suppliers("Acme", "test")

    def test_notices_zero_award_active_unknown_end_and_too_small_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            source = {"Organisation Name": "West Berkshire Council", "Notice Identifier": "n", "Title": "Framework", "Contract start date": "01/01/2025",
                      "Contract end date": "", "Awarded Date": "01/01/2025", "Published Date": "2025-01-01T00:00:00Z", "Awarded Value": "0",
                      "OJEU Procedure Type": "Open", "Supplier": "[Acme Ltd|Address|NONE||No|No][Beta Ltd|Address|NONE||No|No]"}
            write_csv(data / "contracts.csv", [{**source, "Notice Identifier": str(i)} for i in range(20)])
            pairs, log = load_notices(data, "2026-05-01", "2026-07-31")
            self.assertTrue(log["contracts_present"])
            self.assertEqual(log["zero_value_awards"], 20)
            self.assertEqual(len(pairs), 40)
            self.assertTrue(all(p["active"] for p in pairs))
            write_csv(data / "contracts.csv", [source])
            _, small = load_notices(data, "2026-05-01", "2026-07-31")
            self.assertFalse(small["contracts_present"])

    def test_buyer_identity_keeps_uppercase_but_rejects_other_organisations(self):
        self.assertTrue(is_council_buyer("WEST BERKSHIRE COUNCIL"))
        self.assertTrue(is_council_buyer("  West   Berkshire  "))
        self.assertFalse(is_council_buyer("West Berkshire Council services partner"))
        self.assertFalse(is_council_buyer("Westworks Procurement Ltd"))
        self.assertFalse(is_council_buyer("Reading Borough Council"))
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            source = {"Organisation Name": "West Berkshire Council", "Notice Identifier": "n", "Title": "Framework", "Contract start date": "01/01/2025",
                      "Contract end date": "", "Awarded Date": "01/01/2025", "Published Date": "2025-01-01T00:00:00Z", "Awarded Value": "0",
                      "OJEU Procedure Type": "Open", "Supplier": "[Acme Ltd|Address|NONE||No|No]"}
            records = [{**source, "Notice Identifier": str(i)} for i in range(19)]
            records.append({**source, "Notice Identifier": "uppercase", "Organisation Name": "WEST BERKSHIRE COUNCIL"})
            records.append({**source, "Notice Identifier": "other", "Organisation Name": "Another council mentioning West Berkshire Council"})
            write_csv(data / "contracts.csv", records)
            pairs, log = load_notices(data, "2026-05-01", "2026-07-31")
            self.assertTrue(log["contracts_present"])
            self.assertEqual(log["rows_for_council"], 20)
            self.assertEqual(log["normalised_buyer_variants_kept"], 1)
            self.assertEqual(log["rows_dropped_other_buyers"], 1)
            self.assertIn("uppercase", {n["notice_id"] for n in pairs})


class IndicatorTests(unittest.TestCase):
    def test_thresholds_derived_and_null_parameter_not_guessed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rules.json"
            path.write_text(json.dumps({"rules": [{"rule_id": "A", "type": "threshold", "threshold_low": 123,
                         "threshold_low_inclusive": False, "threshold_high_ref": "STATUTORY", "required_action": "Get three quotes"}],
                         "parameters": {"STATUTORY": {"value": None}}}))
            _, thresholds, skipped = load_rules(path)
            self.assertEqual(thresholds[0]["effective_trigger_pence"], 12301)
            self.assertEqual(len(thresholds), 1)
            self.assertIn("null", skipped[0]["reason"])

    def test_exact_and_company_joins_never_promote_near_matches(self):
        active = [notice(supplier="ACME CONSTRUCTION")]
        self.assertEqual(match_supplier("ACME CONSTRUCTON", "", active, {"ACME CONSTRUCTON"})["match_class"], "near_ratio")
        active[0]["company_number"] = "00123456"
        self.assertEqual(match_supplier("UNRELATED NAME", "00123456", active, {"UNRELATED NAME"})["match_class"], "exact")
        self.assertEqual(match_supplier("CARE SERVICES", "", [notice(supplier="HEALTH SERVICES")], {"CARE SERVICES"})["match_class"], "none")

    def test_threshold_band_inclusive_boundary(self):
        rows = [payment("a", 8999), payment("b", 9000), payment("c", 9999), payment("d", 10000), payment("e", 11000)]
        with tempfile.TemporaryDirectory() as tmp:
            inclusive = threshold_clustering(rows, [threshold()], Path(tmp))
            exclusive = threshold_clustering(rows, [threshold(inclusive=False)], Path(tmp))
            self.assertEqual(inclusive["count"], 2)
            self.assertEqual(exclusive["count"], 3)
            self.assertEqual(inclusive["tiers"][0]["comparator"]["count"], 1)

    def test_split_windows_boundary_and_deoverlap(self):
        rows = [payment("a", 6000), payment("b", 6000, "2026-05-30"), payment("c", 6000, "2026-05-31"), payment("single_above", 11000)]
        with tempfile.TemporaryDirectory() as tmp:
            result = split_purchases(rows, [threshold()], Path(tmp))
            first = result["tiers"][0]["top20"][0]
            self.assertEqual(first["row_ids"], ["a", "b"])
            self.assertEqual(result["tiers"][0]["windows"], 1)
            self.assertNotIn("single_above", first["row_ids"])

    def test_duplicate_calendar_window_and_tiers(self):
        rows = [payment("a", 50123), payment("b", 50123, "2026-05-08", time="08:00:00.000"),
                payment("c", 50124), payment("d", 50123, "2026-05-09")]
        groups = duplicate_groups(rows)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["row_ids"], ["a", "b"])
        self.assertEqual(groups[0]["tier"], "different_time")
        self.assertEqual(groups[0]["excess_pence"], 50123)
        same = duplicate_groups([payment("e", 10000), payment("f", 10000)])
        self.assertEqual(same[0]["tier"], "same_timestamp")

    def test_high_value_uses_observed_months_and_dominant_amount_tag(self):
        suppliers = supplier_totals([payment("a", 9000, tag="grant"), payment("b", 1000)], months=6)
        self.assertEqual(suppliers[0]["dominant_tag"], "grant")
        self.assertTrue(suppliers[0]["multi_tag"])
        self.assertEqual(suppliers[0]["annualised_estimate_pence"], 20000)
        with tempfile.TemporaryDirectory() as tmp:
            output, _ = high_value_suppliers(suppliers, [threshold(25000)], 6, Path(tmp))
            self.assertEqual(output["count"], 0)

    def test_off_contract_publication_floor_and_near_match_separate(self):
        suppliers = supplier_totals([payment("a", 10000, supplier="BIG"), payment("b", 9999, supplier="SMALL")], 12)
        rules = {"rules": [{"rule_id": "PUB", "threshold_low": 100, "threshold_low_inclusive": True, "required_action": "Publish a contract notice"}]}
        matches = {"BIG": {"match_class": "near_ratio"}, "SMALL": {"match_class": "none"}}
        with tempfile.TemporaryDirectory() as tmp:
            output = off_contract(suppliers, matches, rules, 12, {"contracts_present": True, "register_present": False}, Path(tmp))
            self.assertEqual(output["eligible_suppliers"], 1)
            self.assertEqual(output["count"], 1)
            self.assertEqual(output["by_match_class"]["near_ratio"]["count"], 1)

    def test_expired_requires_every_notice_to_have_ended(self):
        suppliers = supplier_totals([payment("a", 10000)], 3)
        ended = notice("old", end="2025-12-31", start="2025-01-01", active=False)
        current = notice("new")
        with tempfile.TemporaryDirectory() as tmp:
            result = expired_notice_spend(suppliers, [ended, current], {"contracts_present": True}, {"rules": []}, Path(tmp), "2026-05-01")
            self.assertEqual(result["count"], 0)
            result = expired_notice_spend(suppliers, [ended], {"contracts_present": True}, {"rules": []}, Path(tmp), "2026-05-01")
            self.assertEqual(result["count"], 1)

    def test_award_ratio_excludes_zero_multi_supplier_and_ambiguous_notices(self):
        suppliers = supplier_totals([payment("a", 10000)], 3)
        with tempfile.TemporaryDirectory() as tmp:
            options = {"contracts_present": True}
            self.assertEqual(spend_vs_award(suppliers, [notice(award=0)], options, {"rules": []}, 3, Path(tmp))["count"], 0)
            self.assertEqual(spend_vs_award(suppliers, [notice(count=2)], options, {"rules": []}, 3, Path(tmp))["count"], 0)
            self.assertEqual(spend_vs_award(suppliers, [notice(), notice("N2")], options, {"rules": []}, 3, Path(tmp))["count"], 0)
            valid = spend_vs_award(suppliers, [notice()], options, {"rules": []}, 3, Path(tmp))
            self.assertEqual(valid["count"], 1)
            self.assertEqual(valid["top20"][0]["contract_days"], 365)
            self.assertAlmostEqual(valid["top20"][0]["ratio"], 3.997262, places=6)

    def test_notice_absence_skips_only_notice_based_tests(self):
        absent = {"contracts_present": False, "register_present": False}
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(off_contract([], {}, {"rules": []}, 3, absent, Path(tmp))["skipped"])
            self.assertTrue(spend_vs_award([], [], absent, {"rules": []}, 3, Path(tmp))["skipped"])
            result, _ = high_value_suppliers(supplier_totals([payment("a", 10000)], 3), [threshold()], 3, Path(tmp))
            self.assertEqual(result["count"], 1)


if __name__ == "__main__":
    unittest.main()
