#!/usr/bin/env python3
"""QA check: traceability of the pack.

1. Every rule in outputs/rules.json is cited by a rated risk (risk-ratings.json),
   a control or a test (audit-plan.json), or listed in rules_not_tested with a reason.
2. Every approved, in-scope risk (auditor-comments.md + risk-register.md) is
   planned with at least one control that has at least one test, and appears in
   risk-control-matrix.md and audit-program.md; nothing unapproved is planned.
3. Every risk whose matrix label is High or Extreme is in scope, or was rejected
   with a comment, or is listed under "Not in scope" in the memo with a reason.
4. outputs/challenges.md exists, every row cites evidence, and no row is open.
Prints PASS/FAIL lines and a summary; exit 0 when clean.
"""
import hashlib, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "outputs"  # an outputs folder to check; default outputs/
CITE = re.compile(r"\[(rule|metric|history):((?:[^\[\]]|\[\d+\])+)\]")
HIGH = {"high", "extreme", "very high"}
EVIDENCE = re.compile(r"CPR-\d+|\$\.[\w.\[\]]+|\b(?:AUD|RT|D|T|C)-\d+|scoring_method")


def table_rows(text, first_col=r"R-\d+"):
    rows = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and re.fullmatch(first_col, cells[0]):
            rows.append(cells)
    return rows


def main():
    fails = []
    gate = subprocess.run([sys.executable, str(ROOT / ".claude/skills/audit-program/build_pack.py"), "--gate"], cwd=ROOT, capture_output=True, text=True)
    if gate.returncode:
        fails.append("human gate validation failed: " + gate.stdout.strip().replace("\n", "; "))
    validation = OUT / "pack-validation.json"
    if not validation.exists():
        fails.append("pack-validation.json missing; successful build required")
    else:
        proof = json.loads(validation.read_text())
        if not proof.get("ready") or not proof.get("sha256"):
            fails.append("pack builder validation did not pass")
        for name, expected in proof.get("sha256", {}).items():
            path = Path(name)
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                fails.append(f"pack artifact changed after validation: {path.name}")
    IN = ROOT / "outputs"  # the register, decisions and inputs always come from the project
    rules = [r["rule_id"] for r in json.loads((IN / "rules.json").read_text())["rules"]]
    ratings = json.loads((IN / "risk-ratings.json").read_text())
    plan = json.loads((OUT / "audit-plan.json").read_text()) if (OUT / "audit-plan.json").exists() else {}
    register = (IN / "risk-register.md").read_text(encoding="utf-8") if (IN / "risk-register.md").exists() else ""
    comments = (IN / "auditor-comments.md").read_text(encoding="utf-8") if (IN / "auditor-comments.md").exists() else ""
    memo = (OUT / "planning-memo.md").read_text(encoding="utf-8") if (OUT / "planning-memo.md").exists() else ""
    matrix = (OUT / "risk-control-matrix.md").read_text(encoding="utf-8") if (OUT / "risk-control-matrix.md").exists() else ""
    program = (OUT / "audit-program.md").read_text(encoding="utf-8") if (OUT / "audit-program.md").exists() else ""
    if not plan: fails.append("audit-plan.json missing")
    for name, content in (("risk-register.md", register), ("auditor-comments.md", comments), ("planning-memo.md", memo), ("risk-control-matrix.md", matrix), ("audit-program.md", program)):
        if not content.strip(): fails.append(name + " missing or empty")

    # 1. rules
    cited = set()
    for r in ratings.get("risks", []):
        cited |= {ref for kind, ref in CITE.findall(json.dumps(r)) if kind == "rule"}
    for r in plan.get("risks", []):
        for c in r.get("controls") or []:
            cited |= {x.split(":", 1)[1] for x in c.get("cites") or [] if x.startswith("rule:")}
        for t in r.get("tests") or []:
            cited |= {x.split(":", 1)[1] for x in t.get("cites") or [] if x.startswith("rule:")}
    not_tested = {}
    for g in plan.get("rules_not_tested") or []:
        for x in g.get("rule_ids") or []:
            not_tested[x] = (g.get("reason") or "").strip()
    missing = [x for x in rules if x not in cited and not not_tested.get(x)]
    if missing:
        fails.append(f"rules with no risk, control, test or reason: {', '.join(missing)}")

    # 2. scope and structure
    summary = {c[0]: {"label": c[5], "band": c[6], "scope": c[8]} for c in table_rows(register) if len(c) >= 9}
    decisions = {c[0]: {"decision": c[4].lower(), "comment": c[5] if len(c) > 5 else ""} for c in table_rows(comments) if len(c) >= 5}
    rat = {r["id"]: r for r in ratings.get("risks", [])}
    approved = [rid for rid in summary if decisions.get(rid, {}).get("decision") in ("approve", "amend") and rat.get(rid, {}).get("recommend_in_scope", True)]
    undecided = [rid for rid in summary if not decisions.get(rid, {}).get("decision")]
    if undecided: fails.append(f"gate not closed: undecided {', '.join(undecided)}")
    planned = {r["id"]: r for r in plan.get("risks", [])}
    for rid in approved:
        r = planned.get(rid)
        if not r:
            fails.append(f"{rid}: approved and in scope but not planned"); continue
        controls = r.get("controls") or []
        tests = r.get("tests") or []
        if not controls: fails.append(f"{rid}: no control")
        for c in controls:
            if not any(t.get("control") == c.get("id") for t in tests):
                fails.append(f"{rid}.{c.get('id')}: control without a test")
        if not re.search(rf"^\| {rid}: ", matrix, re.M): fails.append(f"{rid}: not in risk-control-matrix.md")
        if not re.search(rf"^## {rid}: ", program, re.M): fails.append(f"{rid}: not in audit-program.md")
    for rid in planned:
        if rid not in approved: fails.append(f"{rid}: planned but not an approved, in-scope risk")

    # 3. high risks
    not_in_scope_section = memo.split("**Not in scope**", 1)[1].split("\n## ", 1)[0] if "**Not in scope**" in memo else ""
    for rid, v in summary.items():
        if v["label"].lower() in HIGH and rid not in approved:
            d = decisions.get(rid, {})
            if d.get("decision") == "reject" and d.get("comment"): continue
            if re.search(rf"^- {rid}: .+: .+", not_in_scope_section, re.M): continue
            fails.append(f"{rid}: {v['label']} risk not in scope and no recorded reason")
    for rid, v in decisions.items():
        if v["decision"] == "reject" and rid not in summary and v.get("comment") == "" and not re.search(rf"^- {rid}: ", not_in_scope_section, re.M):
            fails.append(f"{rid}: rejected without a reason")

    # 4. challenges
    ch_path = OUT / "challenges.md"
    n_ch, open_rows = 0, []
    if not ch_path.exists():
        fails.append("challenges.md missing")
    else:
        for cells in table_rows(ch_path.read_text(encoding="utf-8"), r"\d+"):
            if len(cells) < 8: continue
            n_ch += 1
            if not EVIDENCE.search(cells[4]): fails.append(f"challenge #{cells[0]}: no citation in Evidence")
            status = cells[7].strip().lower()
            if status == "open" or not status: open_rows.append(cells[0])
            elif status not in ("resolved", "declined", "for the auditor"):
                fails.append(f"challenge #{cells[0]}: unknown status {status!r}")
            if status in ("resolved", "declined", "for the auditor") and not cells[6].strip():
                fails.append(f"challenge #{cells[0]}: closed without planner response")
        if open_rows: fails.append(f"challenges still open: #{', #'.join(open_rows)}")
        if n_ch == 0: fails.append("challenges.md has no challenge rows")

    for f in fails: print("FAIL ", f)
    print(f"SUMMARY trace: rules={len(rules)} rules_cited={len([x for x in rules if x in cited])} rules_not_tested={len([x for x in rules if x not in cited and not_tested.get(x)])} "
          f"approved_in_scope={len(approved)} planned={len(planned)} high_risks={len([1 for v in summary.values() if v['label'].lower() in HIGH])} challenges={n_ch} open={len(open_rows)} failures={len(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

