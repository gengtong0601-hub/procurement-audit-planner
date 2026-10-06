"""Strict file contracts for the five-stage, human-gated audit workflow."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Workbook(Record):
    file: str
    sheet: str


class Manifest(Record):
    council: str = Field(min_length=2)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    period_start: date
    period_end: date
    contract_rules: str
    spend: list[Workbook] = Field(min_length=1)
    contracts: str
    committee_papers: list[str] = Field(min_length=1)
    auditor_days: int = Field(default=15, ge=1, le=90)
    synthetic: bool = False

    @model_validator(mode="after")
    def dates(self):
        if self.period_end < self.period_start:
            raise ValueError("The audit period ends before it starts.")
        return self


class Citation(Record):
    source_file: str
    page: int = Field(ge=1)
    quote: str = Field(min_length=15)


class Rule(Citation):
    rule_id: str = Field(pattern=r"^RULE-[0-9]{3}$")
    clause: str = Field(min_length=1)
    requirement: str = Field(min_length=10)
    indicator: Literal[
        "threshold_clustering", "split_purchases", "off_contract", "duplicates", "manual_review"
    ]
    threshold: Decimal | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def threshold_required(self):
        if self.indicator in {"threshold_clustering", "split_purchases"} and self.threshold is None:
            raise ValueError("Threshold rules require an explicit threshold from the source.")
        return self


class RuleBook(Record):
    rules: list[Rule] = Field(min_length=1)
    extraction_notes: list[str]


class HistoryItem(Citation):
    item_id: str = Field(pattern=r"^HIST-[0-9]{3}$")
    category: Literal["audit_opinion", "open_action", "registered_risk", "coverage"]
    description: str = Field(min_length=10)
    rule_ids: list[str]


class History(Record):
    items: list[HistoryItem]
    coverage_notes: list[str] = Field(min_length=1)


class Transaction(Record):
    transaction_id: str
    supplier: str
    department: str
    category: str
    payment_date: date
    amount: Decimal
    invoice_number: str
    contract_id: str
    source_file: str
    source_sheet: str
    source_row: int = Field(ge=2)


class Indicator(Record):
    indicator_id: str
    rule_id: str
    kind: str
    transaction_ids: list[str]
    gross_value: Decimal
    count: int
    description: str
    computed_by: str = "procurement_audit/analytics.py"


class Analytics(Record):
    row_count: int
    net_spend: Decimal
    gross_spend: Decimal
    supplier_count: int
    transactions: list[Transaction]
    indicators: list[Indicator]
    parameters: dict
    source_hashes: dict[str, str]


class Risk(Record):
    risk_id: str
    title: str
    rule_ids: list[str]
    indicator_ids: list[str]
    history_ids: list[str]
    likelihood: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    score: int
    rating_rationale: str
    narrative: str


class Register(Record):
    risks: list[Risk]
    method: str


class Decision(Record):
    risk_id: str
    decision: Literal["pending", "approve", "amend", "reject"]
    comment: str = ""
    likelihood: int | None = Field(default=None, ge=1, le=5)
    impact: int | None = Field(default=None, ge=1, le=5)

    @model_validator(mode="after")
    def rationale(self):
        if self.decision in {"amend", "reject"} and not self.comment:
            raise ValueError("Amended and rejected risks require an auditor explanation.")
        if self.decision == "amend" and (self.likelihood is None or self.impact is None):
            raise ValueError("An amendment requires both revised likelihood and impact.")
        if self.decision != "amend" and (self.likelihood is not None or self.impact is not None):
            raise ValueError("Revised ratings may only be supplied with an amendment.")
        return self


class Decisions(Record):
    reviewer: str = Field(min_length=2, max_length=100)
    decisions: list[Decision]


class TestStep(Record):
    test_id: str
    risk_id: str
    rule_ids: list[str]
    objective: str
    control: str
    procedure: str
    evidence: list[str]
    sample_recipe: str
    sample_ids: list[str]
    sample_locations: list[str]
    days: int = Field(ge=1)
    day_start: int
    day_end: int


class Program(Record):
    tests: list[TestStep]
    excluded_rules: dict[str, str]
    document_requests: list[str]
    auditor_days: int


class AgentMessage(Record):
    sender: str
    recipient: str
    message: str


class Check(Record):
    name: str
    passed: bool
    details: str


class Signoff(Record):
    reviewer: str = Field(min_length=2, max_length=100)
    decision: Literal["sign_off", "return_for_revision"]
    comment: str = Field(min_length=5, max_length=3000)


class RiskNarrative(Record):
    risk_id: str
    narrative: str = Field(min_length=20, max_length=3000)


class RiskNarratives(Record):
    items: list[RiskNarrative]


class Challenges(Record):
    notes: list[str] = Field(min_length=1, max_length=12)


class TestAdvice(Record):
    test_id: str
    procedure: str = Field(min_length=20, max_length=4000)
    evidence: list[str] = Field(min_length=1, max_length=20)


class PlanningAdvice(Record):
    items: list[TestAdvice]
