"""Почтовые барьеры: условия, подтверждение, неизвестный исход. Без отправки."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import mail_mcp


class MailChecks(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for name, value in [('ROOT', self.root), ('STATE', self.root/'mail.json')]:
            patcher = patch.object(mail_mcp, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_draft_is_blocked_before_checks(self):
        with self.assertRaisesRegex(ValueError, 'check.py'):
            mail_mcp.prepare_report()

    def test_confirmation_is_required_before_any_send(self):
        with patch.object(mail_mcp.smtplib, 'SMTP') as smtp:
            with self.assertRaises(ValueError):
                mail_mcp.send_report('anything', 'да')
            smtp.assert_not_called()

    def test_failed_checks_block_draft(self):
        (self.root/'.lab').mkdir()
        (self.root/'.lab/checks.json').write_text(json.dumps({'passed': False}))
        with self.assertRaisesRegex(ValueError, 'не прошли'):
            mail_mcp.prepare_report()

    def test_unknown_delivery_is_not_retried(self):
        mail_mcp.save_state({'d': {'status': 'sending_or_unknown', 'message_id': '<id@example.test>'}})
        with patch.object(mail_mcp, 'find_message', return_value=None), patch.object(mail_mcp.smtplib, 'SMTP') as smtp:
            with self.assertRaisesRegex(ValueError, 'неизвестен'):
                mail_mcp.send_report('d', 'Отправить Боссу')
            smtp.assert_not_called()

    def test_received_delivery_returns_existing_message(self):
        mail_mcp.save_state({'d': {'status': 'received_locally', 'message_id': '<id@example.test>'}})
        with patch.object(mail_mcp, 'find_message', return_value={'mailpit_id': 'saved'}), patch.object(mail_mcp.smtplib, 'SMTP') as smtp:
            result = mail_mcp.send_report('d', 'Отправить Боссу')
            self.assertEqual(result['status'], 'already_received_locally')
            smtp.assert_not_called()
