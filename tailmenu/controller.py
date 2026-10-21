"""Background CLI work; all state/UI callbacks are dispatched to the GTK thread."""
from threading import Thread

from tailmenu import tailscale


class Controller:
    def __init__(self, dispatch, changed, error, authenticate):
        self.dispatch = dispatch
        self.changed = changed
        self.error = error
        self.authenticate = authenticate
        self.status = tailscale.TailStatus()
        self.busy = False
        self.checking = False
        self.generation = 0
        self.login_requested = False
        self.seen_urls = set()

    def refresh(self, *_args):
        if not self.checking:
            self.checking = True
            generation = self.generation
            Thread(target=self._read_status, args=(generation,), daemon=True).start()
        return True  # keep the GLib timer alive

    def _read_status(self, generation):
        try:
            status = tailscale.get_status()
        except Exception as exc:
            status = tailscale.TailStatus(error=f"Lecture de l’état impossible : {exc}")
        self.dispatch(self._received_status, generation, status)

    def _received_status(self, generation, status):
        self.checking = False
        if generation != self.generation:
            self.refresh()  # discard a result that predates an action/step
            return False
        self.status = status
        self.changed()
        if self.login_requested and status.auth_url and not status.connected:
            if status.auth_url not in self.seen_urls:
                self.seen_urls.add(status.auth_url)
                self.authenticate(status.auth_url)
        return False  # idle callbacks must never repeat

    def start(self, *commands):
        if self.busy or not commands:
            return
        self.busy = True
        self.seen_urls.clear()
        self._step(commands)

    def _step(self, commands):
        self.generation += 1
        self.login_requested = commands[0][0] == "up"
        # Do not keep claiming that a cached connection is still active.
        self.status = tailscale.TailStatus(backend="Starting")
        self.changed()
        Thread(target=self._execute, args=(commands,), daemon=True).start()
        self.refresh()

    def _execute(self, commands):
        try:
            ok, message = tailscale.action(*commands[0])
        except Exception as exc:
            ok, message = False, f"Action impossible : {exc}"
        self.dispatch(self._finished, commands, ok, message)

    def _finished(self, commands, ok, message):
        if ok and len(commands) > 1:
            self._step(commands[1:])
            return False
        self.generation += 1
        self.busy = False
        self.login_requested = False
        self.status = tailscale.TailStatus()
        self.changed()
        self.refresh()
        if not ok:
            self.error(message or "La commande Tailscale a échoué.")
        return False
