import pytest

from procurement_audit.demo import create_demo
from procurement_audit.workflow import extract_rules, run_analysis


@pytest.fixture
def case(tmp_path):
    folder = tmp_path / "case"
    create_demo(folder)
    extract_rules(folder)
    run_analysis(folder)
    return folder
