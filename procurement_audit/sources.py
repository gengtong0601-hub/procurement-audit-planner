"""PDF extraction and literal source-quote verification. No OCR guesses."""

import re
from decimal import Decimal
from pathlib import Path

from pypdf import PdfReader

from procurement_audit.models import Citation
from procurement_audit.storage import WorkflowError, source_path


def pdf_pages(path: Path) -> list[str]:
    try:
        reader = PdfReader(path)
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        raise WorkflowError(f"Cannot extract PDF: {path.name}") from exc
    if not pages or any(not page.strip() for page in pages):
        raise WorkflowError(
            f"{path.name} contains empty or image-only pages. Supply searchable text/OCR and verify it first."
        )
    return pages


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def verify_citations(case: Path, citations: list[Citation], allowed_files: set[str]):
    cache = {}
    for citation in citations:
        if citation.source_file not in allowed_files:
            raise WorkflowError(f"Citation uses an undeclared source: {citation.source_file}")
        if citation.source_file not in cache:
            cache[citation.source_file] = pdf_pages(source_path(case, citation.source_file))
        pages = cache[citation.source_file]
        if citation.page > len(pages) or normalized(citation.quote) not in normalized(
            pages[citation.page - 1]
        ):
            raise WorkflowError(
                f"Unverified quote in {citation.source_file}, page {citation.page}: {citation.quote[:80]}"
            )


def source_bundle(case: Path, filenames: list[str]) -> list[dict]:
    return [
        {"source_file": filename, "page": index, "text": page}
        for filename in filenames
        for index, page in enumerate(pdf_pages(source_path(case, filename)), 1)
    ]


def verify_rule_thresholds(rules):
    for rule in rules.rules:
        if rule.threshold is not None:
            numbers = {
                Decimal(value.replace(",", ""))
                for value in re.findall(r"(?<![\w.])\d[\d,]*(?:\.\d+)?", rule.quote)
            }
            if rule.threshold not in numbers:
                raise WorkflowError(
                    f"Threshold for {rule.rule_id} does not appear in its verified quote."
                )
