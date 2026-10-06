"""Isolated synthetic fixtures only: no decisions or approvals touch real outputs."""
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / '.claude/skills/risk-assessment/build_register.py'
PACK = ROOT / '.claude/skills/audit-program/build_pack.py'


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='gate-fixture-', dir=ROOT / 'tests')
        self.out = Path(self.tmp.name)
        self.risk = {'id': 'R-01', 'title': 'Synthetic risk fixture',
                     'statement': 'A pattern needs investigation.',
                     'likelihood': {'score': 2, 'justification': 'The indicator recurs [metric:$.count].'},
                     'impact': {'score': 3, 'justification': 'The rule describes the required control [rule:CPR-01].'},
                     'recommend_in_scope': True, 'proposed_focus': 'Check supporting documentation.'}
        self.ratings = {'risks': [copy.deepcopy(self.risk)], 'excluded': []}
        self.put('risk-ratings.json', self.ratings)
        self.put('rules.json', {'rules': [{'rule_id': 'CPR-01', 'clause': '1', 'page': 1, 'verbatim_quote': 'Synthetic rule fixture.'}]})
        self.put('analytics.json', {'count': 4})
        self.put('history.json', {'scoring_method': {'usable': False}})

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, name, content):
        (self.out / name).write_text(json.dumps(content))

    def build(self):
        return subprocess.run([sys.executable, str(REGISTER), str(self.out / 'risk-ratings.json'),
                               '--rules', str(self.out / 'rules.json'), '--analytics', str(self.out / 'analytics.json'),
                               '--history', str(self.out / 'history.json'), '--out-dir', str(self.out)],
                              capture_output=True, text=True)

    def gate(self):
        return subprocess.run([sys.executable, str(PACK), '--gate',
                               '--rules', str(self.out / 'rules.json'), '--analytics', str(self.out / 'analytics.json'),
                               '--ratings', str(self.out / 'risk-ratings.json'), '--register', str(self.out / 'risk-register.md'),
                               '--comments', str(self.out / 'auditor-comments.md')], capture_output=True, text=True)

    def decide(self, action='approve', comment='Synthetic fixture only'):
        p = self.out / 'auditor-comments.md'
        s = p.read_text().replace('Reviewer: \n', 'Reviewer: TEST FIXTURE ONLY\n').replace('Date: \n', 'Date: 2026-01-01\n')
        s = s.replace('| yes |  |  |', '| yes | ' + action + ' | ' + comment + ' |')
        p.write_text(s)

    def test_blank_gate_blocks_planning_and_keeps_blank_decision(self):
        result = self.build()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotEqual(self.gate().returncode, 0)
        self.assertIn('| yes |  |  |', (self.out / 'auditor-comments.md').read_text())
        self.assertFalse(json.loads((self.out / 'gate-evidence.json').read_text())['ready'])

    def test_unresolved_citation_excludes_only_broken_risk_but_fails_run(self):
        bad = copy.deepcopy(self.risk); bad['id'] = 'R-02'
        bad['impact']['justification'] = 'Unsupported [rule:DOES-NOT-EXIST].'
        self.ratings['risks'].append(bad); self.put('risk-ratings.json', self.ratings)
        result = self.build()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('risks kept: 1, excluded by validation: 1', result.stdout)
        self.assertIn('VALIDATION BLOCKED', (self.out / 'risk-register.md').read_text())
        self.assertNotEqual(self.gate().returncode, 0)

    def test_scalar_path_malformed_suffix_rejected(self):
        self.ratings['risks'][0]['likelihood']['justification'] = '[metric:$.count trailing junk]'
        self.put('risk-ratings.json', self.ratings)
        self.assertNotEqual(self.build().returncode, 0)

    def test_malformed_json_stops_with_clear_error(self):
        (self.out / 'risk-ratings.json').write_text('{')
        result = self.build()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('FAIL input:', result.stdout)
        self.assertNotIn('Traceback', result.stderr)

    def test_fake_revision_heading_does_not_bypass_gate(self):
        self.assertEqual(self.build().returncode, 0)
        self.decide()
        p = self.out / 'risk-register.md'
        p.write_text('*Revision 1, following auditor comments*\n' + p.read_text())
        result = self.gate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('changed after revision validation', result.stdout)

    def test_approved_risk_cannot_be_silently_changed(self):
        self.assertEqual(self.build().returncode, 0)
        self.decide()
        self.ratings['risks'][0]['impact']['score'] = 5
        self.ratings['revision'] = {'number': 1, 'changes': []}
        self.put('risk-ratings.json', self.ratings)
        result = self.build()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('changed without an amendment', result.stdout)

    def test_reject_retained_risk_blocks(self):
        self.assertEqual(self.build().returncode, 0)
        self.decide('reject', 'Synthetic exclusion reason')
        self.ratings['revision'] = {'number': 1, 'changes': [{'id': 'R-01', 'action': 'rejected', 'summary': 'Removed'}]}
        self.put('risk-ratings.json', self.ratings)
        result = self.build()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('rejection must remove risk', result.stdout)
        self.assertNotEqual(self.gate().returncode, 0)

    def test_amendment_wrong_score_blocks(self):
        self.assertEqual(self.build().returncode, 0)
        self.decide('amend', 'Raise likelihood to 4')
        self.ratings['risks'][0]['likelihood']['score'] = 3
        self.ratings['revision'] = {'number': 1, 'changes': [{'id': 'R-01', 'action': 'amended', 'summary': 'Raised likelihood'}]}
        self.put('risk-ratings.json', self.ratings)
        self.assertIn('requested likelihood score was not applied', self.build().stdout)

    def test_valid_synthetic_approval_revision_closes_and_tamper_reopens(self):
        self.assertEqual(self.build().returncode, 0)
        self.decide()
        self.ratings['revision'] = {'number': 1, 'changes': []}
        self.put('risk-ratings.json', self.ratings)
        result = self.build()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = self.gate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        with (self.out / 'auditor-comments.md').open('a') as f:
            f.write('\nChanged after validation\n')
        self.assertNotEqual(self.gate().returncode, 0)

    def test_changed_source_evidence_invalidates_scope_approval(self):
        self.assertEqual(self.build().returncode, 0)
        self.decide()
        self.ratings['revision'] = {'number': 1, 'changes': []}
        self.put('risk-ratings.json', self.ratings)
        self.assertEqual(self.build().returncode, 0)
        self.put('analytics.json', {'count': 999})
        self.assertNotEqual(self.gate().returncode, 0)

    def test_adverse_uplift_requires_adverse_audit(self):
        self.ratings['risks'][0]['repeat_finding'] = {'history_id': 'AUD-01', 'base_likelihood': 1}
        self.ratings['risks'][0]['likelihood']['justification'] += ' [history:AUD-01]'
        self.put('risk-ratings.json', self.ratings)
        self.put('history.json', {'scoring_method': {'usable': False}, 'audits': [{'id': 'AUD-01', 'assurance_opinion': 'Reasonable'}]})
        self.assertIn('adverse assurance opinion', self.build().stdout)

    def test_qa_missing_artifacts_never_pass(self):
        for name in ('check_samples.py', 'check_numbers.py'):
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/checks' / name), str(self.out)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0, name)
            self.assertIn('missing', result.stdout, name)


if __name__ == '__main__':
    unittest.main()
