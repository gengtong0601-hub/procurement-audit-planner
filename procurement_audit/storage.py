"""Safe case-local artifacts and source integrity checks."""

import hashlib
import json
import os
from pathlib import Path

from pydantic import BaseModel

from procurement_audit.models import Manifest


class WorkflowError(ValueError):
    """A missing input, unverified source, or incomplete human gate."""


def read_json(path: Path):
    if not path.is_file():
        raise WorkflowError(f"Missing required input: {path.name}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise WorkflowError(f"Cannot read JSON file: {path.name}") from exc


def write_json(path: Path, data):
    value = data.model_dump(mode="json") if isinstance(data, BaseModel) else data
    write_text(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def source_path(case: Path, filename: str) -> Path:
    root = (case / "inputs").resolve()
    path = (root / filename).resolve()
    if not path.is_relative_to(root) or path == root:
        raise WorkflowError("Source paths must stay inside the case inputs directory.")
    if not path.is_file():
        raise WorkflowError(f"Missing required source: {filename}")
    return path


def load_manifest(case: Path) -> Manifest:
    manifest = Manifest.model_validate(read_json(case / "inputs/manifest.json"))
    names = [manifest.contract_rules, manifest.contracts, *manifest.committee_papers]
    names.extend(item.file for item in manifest.spend)
    for name in names:
        source_path(case, name)
    return manifest


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes(case: Path) -> dict[str, str]:
    manifest = load_manifest(case)
    names = {manifest.contract_rules, manifest.contracts, *manifest.committee_papers}
    names.update(item.file for item in manifest.spend)
    result = {name: digest(source_path(case, name)) for name in sorted(names)}
    result["manifest.json"] = digest(case / "inputs/manifest.json")
    return result


def outputs(case: Path) -> Path:
    return case / "outputs"
