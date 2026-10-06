"""A host's optional Poppler installation must not change source verification."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("script,args", [
    (".claude/skills/extract-rules/verify_quotes.py", ["outputs/rules.json", "data/contract-rules.pdf"]),
    ("scripts/verify_history.py", ["outputs/history.json", "data/committee"]),
])
def test_quote_checks_use_same_extractor_with_poppler_installed(tmp_path, script, args):
    other_extractor = tmp_path / "pdftotext"
    other_extractor.write_text("#!/bin/sh\nprintf 'Different PDF extraction order'\n")
    other_extractor.chmod(0o755)
    environment = dict(os.environ, PATH=str(tmp_path) + os.pathsep + os.environ.get("PATH", ""))
    result = subprocess.run([sys.executable, str(ROOT / script), *args], cwd=ROOT,
                            env=environment, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ALL CHECKS PASSED" in result.stdout
