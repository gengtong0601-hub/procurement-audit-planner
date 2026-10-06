PYTHON := .venv/bin/python

.PHONY: setup analyse verify test serve gate
setup:
	python3 -m venv .venv
	$(PYTHON) -m pip install -r requirements.txt
analyse:
	$(PYTHON) scripts/clean.py
	$(PYTHON) scripts/analyse.py
verify:
	$(PYTHON) .claude/skills/extract-rules/verify_quotes.py outputs/rules.json data/contract-rules.pdf
	$(PYTHON) scripts/verify_history.py outputs/history.json data/committee
	$(PYTHON) scripts/selfcheck.py
test:
	$(PYTHON) -m pytest -q --basetemp runtime/test-temp
serve:
	$(PYTHON) -m harness.app
gate:
	$(PYTHON) .claude/skills/audit-program/build_pack.py --gate
