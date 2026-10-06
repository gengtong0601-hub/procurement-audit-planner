# Example inputs

Run `python -m procurement_audit.cli demo --case .audit-cases/demo` after installation.
The generator writes a searchable Contract Rules PDF, committee PDF, spend workbook,
contracts CSV, manifest and reviewed rule/history candidates. All data is synthetic
and explicitly labeled. It runs through analysis and stops at the first human gate.

Expected synthetic population: 12 rows, GBP 467,000 net and GBP 511,000 gross.
Threshold indicator: PAY-001, PAY-002. Split indicator: PAY-001, PAY-002, PAY-003.
Contract indicator: PAY-006. Duplicate indicator: PAY-004, PAY-005.
The negative credit PAY-009 remains in the population and is a relevant alternative
explanation to investigate for the duplicate indicator.

There are five risks, including the manual conflict-control review. Four historical
items and five rules contain source-verified quotes. Human decisions are not generated.
