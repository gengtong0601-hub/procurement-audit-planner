"""Create clearly labeled synthetic PDFs, XLSX and CSV for a reproducible demonstration."""

import csv
from pathlib import Path

from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from procurement_audit.storage import WorkflowError, write_json

RULE_TEXT = [
    "1.1 Purchases with a total value of GBP 100000 or more must use an open tender procedure.",
    "1.2 Requirements must not be split into smaller purchases to avoid the GBP 100000 tender threshold.",
    "2.1 All procurement payments must be supported by a valid contract covering the supplier and category.",
    "2.2 Before releasing payment, officers must check that the supplier invoice has not already been paid.",
    "3.1 Procurement officers must record and manage any declared conflicts of interest.",
]
HISTORY_TEXT = [
    "The 2024 procurement audit gave a limited assurance opinion because contract records were incomplete.",
    "Action A17 remains open: reconcile the internal contract register and retain evidence of completion.",
    "The committee registered a risk that duplicate invoices may not be detected before payment.",
    "Prior audit work covered contract register maintenance and invoice controls; conflicts were not reviewed.",
]


def make_pdf(path: Path, title: str, paragraphs: list[str]):
    canvas = Canvas(str(path), pagesize=A4)
    canvas.setTitle(title)
    text = canvas.beginText(40, 800)
    text.setFont("Helvetica", 11)
    text.textLine(title)
    text.textLine("SYNTHETIC TRAINING DATA - NOT A REAL COUNCIL")
    text.textLine("")
    import textwrap

    for paragraph in paragraphs:
        for line in textwrap.wrap(paragraph, 85):
            text.textLine(line)
        text.textLine("")
    canvas.drawText(text)
    canvas.save()


def create_demo(case: Path):
    if case.exists() and any(case.iterdir()):
        raise WorkflowError(
            "Demo destination must be new or empty; existing cases are never overwritten."
        )
    inputs = case / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    make_pdf(inputs / "contract-rules.pdf", "Example Borough Contract Procedure Rules", RULE_TEXT)
    make_pdf(
        inputs / "committee-papers.pdf",
        "Example Borough Audit Committee - March 2025",
        HISTORY_TEXT,
    )
    write_json(
        inputs / "manifest.json",
        {
            "council": "Example Borough (synthetic)",
            "currency": "GBP",
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
            "contract_rules": "contract-rules.pdf",
            "contracts": "contracts.csv",
            "spend": [{"file": "spend.xlsx", "sheet": "Payments"}],
            "committee_papers": ["committee-papers.pdf"],
            "auditor_days": 15,
            "synthetic": True,
        },
    )
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Payments"
    sheet.append(
        [
            "transaction_id",
            "supplier",
            "department",
            "category",
            "payment_date",
            "amount",
            "invoice_number",
            "contract_id",
        ]
    )
    rows = [
        ["PAY-001", "Atlas Works", "Estates", "Repairs", "2025-02-01", 95000, "AT-101", "C-001"],
        ["PAY-002", "Atlas Works", "Estates", "Repairs", "2025-02-12", 92000, "AT-102", "C-001"],
        ["PAY-003", "Atlas Works", "Estates", "Repairs", "2025-02-25", 45000, "AT-103", "C-001"],
        ["PAY-004", "Beacon Digital", "IT", "Software", "2025-03-01", 22000, "BD-008", "C-002"],
        ["PAY-005", "Beacon Digital", "IT", "Software", "2025-03-08", 22000, "BD-008", "C-002"],
        ["PAY-006", "Cedar Services", "Housing", "Consulting", "2025-04-01", 130000, "CS-101", ""],
        [
            "PAY-007",
            "Delta Supplies",
            "Schools",
            "Stationery",
            "2025-04-04",
            3000,
            "DS-201",
            "C-004",
        ],
        ["PAY-008", "Elm Travel", "Transport", "Travel", "2025-05-01", 5000, "ET-111", "C-005"],
        ["PAY-009", "Beacon Digital", "IT", "Software", "2025-06-01", -22000, "CR-BD-008", "C-002"],
        ["PAY-010", "Ferry Energy", "Estates", "Energy", "2025-07-01", 65000, "FE-301", "C-006"],
        [
            "PAY-011",
            "Delta Supplies",
            "Schools",
            "Stationery",
            "2025-08-01",
            1000,
            "DS-202",
            "C-004",
        ],
        ["PAY-012", "Grove Learning", "HR", "Training", "2025-09-01", 9000, "GL-101", "C-007"],
    ]
    for row in rows:
        sheet.append(row)
    workbook.save(inputs / "spend.xlsx")
    with (inputs / "contracts.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["contract_id", "supplier", "category", "start_date", "end_date"])
        for cid, supplier, category in [
            ("C-001", "Atlas Works", "Repairs"),
            ("C-002", "Beacon Digital", "Software"),
            ("C-004", "Delta Supplies", "Stationery"),
            ("C-005", "Elm Travel", "Travel"),
            ("C-006", "Ferry Energy", "Energy"),
            ("C-007", "Grove Learning", "Training"),
        ]:
            writer.writerow([cid, supplier, category, "2025-01-01", "2025-12-31"])
    kinds = [
        "threshold_clustering",
        "split_purchases",
        "off_contract",
        "duplicates",
        "manual_review",
    ]
    write_json(
        inputs / "rule-candidates.json",
        {
            "rules": [
                {
                    "rule_id": f"RULE-{index:03}",
                    "clause": text.split(" ")[0],
                    "quote": text,
                    "source_file": "contract-rules.pdf",
                    "page": 1,
                    "requirement": text.split(" ", 1)[1],
                    "indicator": kind,
                    "threshold": "100000" if index <= 2 else None,
                }
                for index, (text, kind) in enumerate(zip(RULE_TEXT, kinds, strict=True), 1)
            ],
            "extraction_notes": [
                "Human-authored synthetic proposals; each quote is verified against the generated PDF."
            ],
        },
    )
    categories = ["audit_opinion", "open_action", "registered_risk", "coverage"]
    write_json(
        inputs / "history-candidates.json",
        {
            "items": [
                {
                    "item_id": f"HIST-{index:03}",
                    "source_file": "committee-papers.pdf",
                    "page": 1,
                    "quote": text,
                    "description": text,
                    "category": category,
                    "rule_ids": ["RULE-003"] if index <= 2 else ["RULE-004"],
                }
                for index, (text, category) in enumerate(
                    zip(HISTORY_TEXT, categories, strict=True), 1
                )
            ],
            "coverage_notes": [
                "Synthetic 2024 audit coverage concerned contracts and invoices; conflict controls remain a coverage gap."
            ],
        },
    )
    return case
