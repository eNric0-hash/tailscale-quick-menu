import json
import unittest
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
        self.assertEqual(tailscale.get_status(), tailscale.TailStatus())


if __name__ == "__main__":
    unittest.main()
