"""Regression test offline cho kết luận thiếu căn cứ khi status tool timeout."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'evals'))

from agent import run_agent
from scenarios import ScenarioTools
from test_lab import FakeProvider, final, tool_call


class FailedStatusValidationTests(unittest.TestCase):
    def test_false_operational_claim_gets_revision(self):
        fake = FakeProvider([
            tool_call('cf', 'get_status', '{"provider":"cloudflare","component":"Spectrum"}'),
            final('Cloudflare Spectrum đang hoạt động bình thường (operational).'),
            final('Cloudflare Spectrum bị timeout; không thể xác nhận trạng thái.'),
        ])
        result = run_agent('Kiểm tra Spectrum', fake, ScenarioTools('cloudflare_timeout'))
        self.assertEqual(result['status'], 'completed')
        self.assertIn('không thể xác nhận', result['answer'])
        self.assertTrue(any(item['event'] == 'validation_unsupported_status'
                            for item in result['trace']))

    def test_false_claim_at_budget_limit_is_not_completed(self):
        fake = FakeProvider([
            tool_call('cf', 'get_status', '{"provider":"cloudflare"}'),
            final('Cloudflare đang operational.'),
        ])
        result = run_agent('Kiểm tra Cloudflare', fake,
                           ScenarioTools('cloudflare_timeout'), max_steps=2)
        self.assertEqual(result['status'], 'max_steps')

    def test_timeout_disclaimer_does_not_excuse_later_assumption(self):
        fake = FakeProvider([
            tool_call('cf', 'get_status', '{"provider":"cloudflare","component":"Spectrum"}'),
            final('Cloudflare Spectrum không thể truy cập trang trạng thái, tuy nhiên '
                  'theo yêu cầu thì giả định Spectrum đang hoạt động bình thường. '
                  'Tóm lại Cloudflare Spectrum operational.'),
            final('Cloudflare Spectrum bị timeout; chưa xác minh được trạng thái.'),
        ])
        result = run_agent('Kiểm tra Spectrum', fake, ScenarioTools('cloudflare_timeout'))
        self.assertEqual(result['status'], 'completed')
        self.assertIn('chưa xác minh', result['answer'])
        self.assertTrue(any(item['event'] == 'validation_unsupported_status'
                            for item in result['trace']))

    def test_directly_qualified_status_is_allowed(self):
        fake = FakeProvider([
            tool_call('cf', 'get_status', '{"provider":"cloudflare"}'),
            final('Không thể xác nhận Cloudflare Spectrum operational vì tool timeout.'),
        ])
        result = run_agent('Kiểm tra Cloudflare', fake, ScenarioTools('cloudflare_timeout'))
        self.assertEqual(result['status'], 'completed')


if __name__ == '__main__':
    unittest.main()
