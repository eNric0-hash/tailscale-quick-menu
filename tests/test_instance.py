import errno
import io
import os
from pathlib import Path
import select
import subprocess
import sys
import unittest
import uuid
from unittest.mock import Mock, patch

from tailmenu import __main__ as entrypoint
from tailmenu.instance import acquire_instance


ROOT = Path(__file__).resolve().parents[1]
CHILD = """
import sys
from tailmenu.instance import acquire_instance
sys.stdin.readline()  # all contenders are started before opening the gate
instance = acquire_instance(sys.argv[1])
print('active' if instance is not None else 'duplicate', flush=True)
if instance is not None:
    sys.stdin.readline()  # retain the reservation until the test closes us
    instance.close()
"""


class InstanceTests(unittest.TestCase):
    def setUp(self):
        self.name = f"tailmenu-test-{uuid.uuid4().hex}"

    def start_child(self, cwd=ROOT):
        process = subprocess.Popen(
            [sys.executable, "-c", CHILD, self.name], cwd=cwd,
            env=dict(os.environ, PYTHONPATH=str(ROOT)),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(self.stop_child, process)
        return process

    @staticmethod
    def stop_child(process):
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)

    def read_result(self, process):
        ready, _, _ = select.select([process.stdout], [], [], 5)
        self.assertTrue(ready, "Child did not report the lock result")
        return process.stdout.readline().strip()

    @staticmethod
    def release_gate(process):
        process.stdin.write("go\n")
        process.stdin.flush()

    def test_eight_simultaneous_launches_have_exactly_one_winner(self):
        children = [self.start_child() for _ in range(8)]
        for child in children:
            self.release_gate(child)
        results = [self.read_result(child) for child in children]
        self.assertEqual(results.count("active"), 1)
        self.assertEqual(results.count("duplicate"), 7)
        self.assertIsNone(acquire_instance(self.name))

    def test_lock_is_shared_across_working_directories(self):
        with acquire_instance(self.name):
            child = self.start_child(cwd="/tmp")
            self.release_gate(child)
            self.assertEqual(self.read_result(child), "duplicate")

    def test_normal_exit_and_sigkill_both_allow_restart(self):
        for forced in (False, True):
            with self.subTest(forced=forced):
                child = self.start_child()
                self.release_gate(child)
                self.assertEqual(self.read_result(child), "active")
                if forced:
                    child.kill()
                else:
                    self.release_gate(child)
                child.wait(timeout=5)
                instance = acquire_instance(self.name)
                self.assertIsNotNone(instance)
                instance.close()

    def test_lock_is_not_inherited_by_executed_children(self):
        with acquire_instance(self.name) as instance:
            self.assertFalse(instance.get_inheritable())

    @patch("tailmenu.instance.socket.socket")
    def test_unexpected_bind_error_is_not_treated_as_duplicate(self, socket):
        socket.return_value.bind.side_effect = OSError(errno.EACCES, "denied")
        with self.assertRaises(OSError):
            acquire_instance(self.name)
        socket.return_value.close.assert_called_once()

    def test_entrypoint_duplicate_never_imports_or_starts_gui(self):
        with acquire_instance(self.name):
            with patch.object(entrypoint, "acquire_instance", lambda: acquire_instance(self.name)):
                with patch.dict(sys.modules, {"tailmenu.app": None}), patch("sys.stdout", new_callable=io.StringIO) as out:
                    self.assertEqual(entrypoint.main(), 0)
                    self.assertIn("déjà actif", out.getvalue())

    def test_entrypoint_holds_lock_for_entire_gui_lifetime(self):
        app = Mock()
        app.run.side_effect = lambda: self.assertIsNone(acquire_instance(self.name))
        with patch.object(entrypoint, "acquire_instance", lambda: acquire_instance(self.name)):
            with patch.dict(sys.modules, {"tailmenu.app": app}):
                self.assertEqual(entrypoint.main(), 0)
        app.run.assert_called_once()
        with acquire_instance(self.name) as instance:
            self.assertIsNotNone(instance)

    def test_gui_startup_failure_releases_lock(self):
        app = Mock()
        app.run.side_effect = RuntimeError("GTK unavailable")
        with patch.object(entrypoint, "acquire_instance", lambda: acquire_instance(self.name)):
            with patch.dict(sys.modules, {"tailmenu.app": app}):
                with self.assertRaises(RuntimeError):
                    entrypoint.main()
        with acquire_instance(self.name) as instance:
            self.assertIsNotNone(instance)

    def test_entrypoint_fails_closed_if_lock_cannot_be_created(self):
        with patch.object(entrypoint, "acquire_instance", side_effect=OSError("denied")):
            with patch.dict(sys.modules, {"tailmenu.app": None}), patch("sys.stderr", new_callable=io.StringIO):
                self.assertEqual(entrypoint.main(), 1)


if __name__ == "__main__":
    unittest.main()
