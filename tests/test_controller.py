import queue
import threading
import unittest
from unittest.mock import Mock, call, patch

from tailmenu.controller import Controller
from tailmenu.tailscale import TailStatus


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.events = queue.Queue()
        self.changed = Mock()
        self.errors = Mock()
        self.auth = Mock()
        self.controller = Controller(
            lambda fn, *args: self.events.put((fn, args)),
            self.changed, self.errors, self.auth,
        )

    def pump_until(self, predicate):
        for _ in range(30):
            if predicate():
                return
            fn, args = self.events.get(timeout=2)
            self.assertFalse(fn(*args), "Idle callbacks must run only once")
        self.fail("Controller failed to settle")

    @patch("tailmenu.controller.tailscale.get_status", return_value=TailStatus())
    @patch("tailmenu.controller.tailscale.action")
    def test_login_wait_does_not_block_refresh_or_open_repeated_tabs(self, action, status):
        started, release, done = threading.Event(), threading.Event(), threading.Event()

        def blocked_action(*args):
            started.set()
            try:
                release.wait(3)
                return True, ""
            finally:
                done.set()

        action.side_effect = blocked_action
        status.return_value = TailStatus(backend="NeedsLogin", auth_url="https://login.tailscale.com/a/test")
        self.controller.status = TailStatus(connected=True)
        try:
            self.controller.start(("up",))
            self.assertTrue(started.wait(1))
            self.assertTrue(self.controller.busy)
            self.assertFalse(self.controller.status.connected)
            self.pump_until(lambda: self.auth.called)
            self.assertTrue(self.controller.busy)
            self.controller.refresh()
            self.pump_until(lambda: not self.controller.checking)
            self.auth.assert_called_once_with(status.return_value.auth_url)
            self.controller.start(("logout",))
            self.assertEqual(action.call_count, 1)
        finally:
            release.set()
            done.wait(2)
        self.pump_until(lambda: not self.controller.busy and not self.controller.checking)

    @patch("tailmenu.controller.tailscale.get_status", return_value=TailStatus())
    @patch("tailmenu.controller.tailscale.action", return_value=(False, "Autorisation refusée"))
    def test_logout_failure_never_starts_up(self, action, status):
        self.controller.start(("logout",), ("up",))
        self.pump_until(lambda: not self.controller.busy and not self.controller.checking)
        action.assert_called_once_with("logout")
        self.errors.assert_called_once_with("Autorisation refusée")

    @patch("tailmenu.controller.tailscale.get_status", return_value=TailStatus())
    @patch("tailmenu.controller.tailscale.action", return_value=(True, ""))
    def test_account_switch_runs_in_order(self, action, status):
        self.controller.start(("logout",), ("up",))
        self.pump_until(lambda: not self.controller.busy and not self.controller.checking)
        self.assertEqual(action.call_args_list, [call("logout"), call("up")])
        self.errors.assert_not_called()

    @patch("tailmenu.controller.tailscale.get_status", return_value=TailStatus())
    @patch("tailmenu.controller.tailscale.action", side_effect=RuntimeError("failure"))
    def test_worker_exception_does_not_leave_actions_disabled(self, action, status):
        self.controller.start(("down",))
        self.pump_until(lambda: not self.controller.busy and not self.controller.checking)
        self.errors.assert_called_once()

    @patch("tailmenu.controller.tailscale.get_status", return_value=TailStatus(backend="Stopped"))
    def test_stale_connected_snapshot_cannot_overwrite_new_state(self, status):
        self.controller.generation = 2
        self.controller.checking = True
        self.controller._received_status(1, TailStatus(connected=True))
        self.assertFalse(self.controller.status.connected)
        self.pump_until(lambda: not self.controller.checking)
        self.assertEqual(self.controller.status.backend, "Stopped")

    @patch("tailmenu.controller.tailscale.get_status", side_effect=RuntimeError("bad data"))
    def test_status_exception_clears_previous_connected_state(self, status):
        self.controller.status = TailStatus(connected=True)
        self.controller.refresh()
        self.pump_until(lambda: not self.controller.checking)
        self.assertFalse(self.controller.status.connected)
        self.assertTrue(self.controller.status.error)

    @patch("tailmenu.controller.Thread")
    def test_overlapping_refreshes_are_coalesced(self, thread):
        self.controller.refresh()
        self.controller.refresh()
        thread.assert_called_once()

    def test_background_refresh_does_not_open_login_without_user_action(self):
        self.controller._received_status(0, TailStatus(backend="NeedsLogin", auth_url="https://login.tailscale.com/a/test"))
        self.auth.assert_not_called()
