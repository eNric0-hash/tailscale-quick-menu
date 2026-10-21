import json
import unittest
import subprocess
from unittest.mock import patch

from tailmenu import tailscale


class StatusTests(unittest.TestCase):
    @patch("tailmenu.tailscale._run")
    def test_reads_connected_status_and_exit_nodes(self, run):
        payload = {
            "BackendState": "Running",
            "Self": {"Online": True, "HostName": "blazz", "UserID": 1234, "TailscaleIPs": ["100.64.1.2", "fd7a::1"]},
            "User": {"1234": {"LoginName": "blazeur@example.com"}},
            "Peer": {"x": {"ExitNodeOption": True, "HostName": "paris", "TailscaleIPs": ["100.70.1.4"]}},
        }
        run.return_value.returncode = 0
        run.return_value.stdout = json.dumps(payload)
        status = tailscale.get_status()
        self.assertTrue(status.connected)
        self.assertEqual(status.account, "blazeur@example.com")
        self.assertEqual(status.ip, "100.64.1.2")
        self.assertEqual(status.exit_nodes, [("paris", "100.70.1.4")])

    @patch("tailmenu.tailscale._run")
    def test_handles_unavailable_daemon(self, run):
        run.return_value.returncode = 1
        run.return_value.stderr = "daemon unavailable"
        status = tailscale.get_status()
        self.assertFalse(status.connected)
        self.assertEqual(status.label, "État indisponible")
        self.assertEqual(status.error, "daemon unavailable")

    @patch("tailmenu.tailscale._run")
    def test_never_claims_connected_for_offline_or_missing_self(self, run):
        run.return_value.returncode = 0
        for node in (None, {}, {"Online": False}, {"Online": "true"}):
            with self.subTest(node=node):
                run.return_value.stdout = json.dumps({"BackendState": "Running", "Self": node})
                self.assertFalse(tailscale.get_status().connected)

    @patch("tailmenu.tailscale._run")
    def test_authentication_and_stopped_states(self, run):
        run.return_value.returncode = 0
        for backend in ("NeedsLogin", "NeedsMachineAuth", "Starting", "Stopped"):
            with self.subTest(backend=backend):
                run.return_value.stdout = json.dumps({
                    "BackendState": backend, "Self": {"Online": True},
                    "AuthURL": "https://login.tailscale.com/a/example",
                })
                status = tailscale.get_status()
                self.assertFalse(status.connected)
                self.assertEqual(status.backend, backend)
                self.assertEqual(status.auth_url, "https://login.tailscale.com/a/example")

    @patch("tailmenu.tailscale._run")
    def test_invalid_status_and_missing_command(self, run):
        run.return_value.returncode = 0
        for payload in ("bad json", "null", "[]"):
            run.return_value.stdout = payload
            self.assertTrue(tailscale.get_status().error)
        for exc in (FileNotFoundError("tailscale"), subprocess.TimeoutExpired("tailscale", 8)):
            run.side_effect = exc
            self.assertTrue(tailscale.get_status().error)

    def test_rejects_non_web_auth_urls(self):
        for value in (None, 1, "file:///etc/passwd", "javascript:alert(1)", "https:///", "http://[", "https://user@example.com"):
            self.assertEqual(tailscale.login_url(value), "")


class ActionTests(unittest.TestCase):
    @patch("tailmenu.tailscale.subprocess.run")
    def test_up_has_bounded_wait_and_preserves_settings(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, "", "")
        self.assertTrue(tailscale.action("up")[0])
        run.assert_called_once_with(
            ["pkexec", "tailscale", "up", "--timeout=180s"],
            text=True, capture_output=True, check=False, timeout=210,
        )

    @patch("tailmenu.tailscale.subprocess.run")
    def test_status_has_short_timeout_without_privilege_prompt(self, run):
        run.return_value = subprocess.CompletedProcess([], 1, "", "stopped")
        tailscale.get_status()
        run.assert_called_once_with(
            ["tailscale", "status", "--json"], text=True,
            capture_output=True, check=False, timeout=8,
        )

    @patch("tailmenu.tailscale._run")
    def test_command_failures_always_have_message(self, run):
        for code in (1, 126, 127):
            run.return_value = subprocess.CompletedProcess([], code, "", "")
            ok, message = tailscale.action("logout")
            self.assertFalse(ok)
            self.assertTrue(message)
        for exc in (FileNotFoundError("pkexec"), subprocess.TimeoutExpired("pkexec", 210)):
            run.side_effect = exc
            ok, message = tailscale.action("up")
            self.assertFalse(ok)
            self.assertTrue(message)


if __name__ == "__main__":
    unittest.main()
