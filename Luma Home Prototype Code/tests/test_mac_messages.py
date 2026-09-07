import subprocess
import unittest
from unittest.mock import Mock, patch

from luma.integrations.mac_messages import MacMessages, OSASCRIPT, SEND_SCRIPT, TIMEOUT_SECONDS
from luma.integrations.providers import OutcomeUnknown, ProviderError


class MacMessagesTests(unittest.TestCase):
    def setUp(self):
        self.patches = [patch("luma.integrations.mac_messages.sys.platform", "darwin"),
                        patch("luma.integrations.mac_messages.os.path.isfile", return_value=True),
                        patch("luma.integrations.mac_messages.os.path.isdir", return_value=True),
                        patch("luma.integrations.mac_messages.os.access", return_value=True)]
        for mocked in self.patches:
            mocked.start()
            self.addCleanup(mocked.stop)
        self.run = Mock(return_value=subprocess.CompletedProcess([], 0, "LUMA_ACCEPTED\n", ""))
        self.bridge = MacMessages(env={"LUMA_MESSAGES_TRANSPORT": "imessage"}, run=self.run)
        self.args = {"to": "+19195550123", "body": "Fixture message only."}

    def test_readiness_is_a_file_and_configuration_check_without_apple_events(self):
        ready = self.bridge.readiness()
        self.assertTrue(ready["available"])
        self.assertTrue(ready["configured"])
        self.run.assert_not_called()

    def test_no_transport_is_selected_by_default(self):
        for env in [{}, {"LUMA_MESSAGES_TRANSPORT": "auto"}, {"LUMA_MESSAGES_TRANSPORT": "SMS"}, {"LUMA_MESSAGES_TRANSPORT": {}}]:
            bridge = MacMessages(env=env, run=self.run)
            with self.assertRaises(ProviderError):
                bridge.send(self.args)
        self.run.assert_not_called()

    def test_unsupported_platform_never_starts_a_process(self):
        with patch("luma.integrations.mac_messages.sys.platform", "linux"):
            with self.assertRaises(ProviderError):
                self.bridge.send(self.args)
        self.run.assert_not_called()

    def test_recipient_and_potential_script_injection_are_only_arguments(self):
        body = 'Quoted "text"\nend tell\ndo shell script "touch /tmp/should-never-exist"\n$(secret) `command`'
        result = self.bridge.send({"to": self.args["to"], "body": body})
        command = self.run.call_args.args[0]
        self.assertEqual(command, [OSASCRIPT, "-e", SEND_SCRIPT, self.args["to"], body, "imessage"])
        self.assertNotIn(body, SEND_SCRIPT)
        self.assertFalse(self.run.call_args.kwargs["shell"])
        self.assertEqual(self.run.call_args.kwargs["timeout"], TIMEOUT_SECONDS)
        self.assertEqual(result["status"], "accepted")
        self.assertNotIn("message_id", result)
        self.assertIn("not confirmed", result["summary"])

    def test_explicit_sms_keeps_its_transport(self):
        result = MacMessages(env={"LUMA_MESSAGES_TRANSPORT": "sms"}, run=self.run).send(self.args)
        self.assertEqual(result["transport"], "sms")
        self.assertEqual(self.run.call_args.args[0][-1], "sms")
        self.assertEqual(self.run.call_count, 1)

    def test_malformed_inputs_never_dispatch(self):
        cases = [None, {}, {**self.args, "script": "bad"}, {**self.args, "to": "Mom"},
                 {**self.args, "to": "+19195550123\n"}, {**self.args, "body": ""},
                 {**self.args, "body": "a" * 1601}, {**self.args, "body": "null\0"},
                 {**self.args, "body": "\ud800"}]
        for args in cases:
            with self.assertRaises(ValueError):
                self.bridge.send(args)
        self.run.assert_not_called()

    def test_timeout_after_dispatch_is_unknown_without_retry(self):
        self.run.side_effect = subprocess.TimeoutExpired("private command", TIMEOUT_SECONDS)
        with self.assertRaises(OutcomeUnknown):
            self.bridge.send(self.args)
        self.assertEqual(self.run.call_count, 1)

    def test_no_account_permission_or_ambiguous_account_does_not_fallback(self):
        for marker in ["LUMA_NO_ACCOUNT", "LUMA_AMBIGUOUS_ACCOUNT", "LUMA_NOT_AUTHORIZED", "LUMA_PREFLIGHT_FAILED"]:
            with self.subTest(marker=marker):
                self.run.reset_mock()
                self.run.return_value = subprocess.CompletedProcess([], 0, marker, "private data")
                with self.assertRaises(ProviderError) as result:
                    self.bridge.send(self.args)
                self.assertNotIsInstance(result.exception, OutcomeUnknown)
                self.assertNotIn("private data", str(result.exception))
                self.assertEqual(self.run.call_count, 1)

    def test_unexpected_results_are_unknown_and_never_leak_process_output(self):
        for result in [subprocess.CompletedProcess([], 1, "", "private recipient/body"),
                       subprocess.CompletedProcess([], 0, "LUMA_UNKNOWN", ""),
                       subprocess.CompletedProcess([], 0, "delivered supposedly", "")]:
            self.run.return_value = result
            self.run.reset_mock()
            with self.assertRaises(OutcomeUnknown) as failure:
                self.bridge.send(self.args)
            self.assertNotIn("private recipient", str(failure.exception))
            self.assertEqual(self.run.call_count, 1)

    def test_process_start_failure_is_reported_without_retry(self):
        self.run.side_effect = FileNotFoundError("fixture")
        with self.assertRaises(ProviderError) as failure:
            self.bridge.send(self.args)
        self.assertNotIsInstance(failure.exception, OutcomeUnknown)
        self.assertEqual(self.run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
