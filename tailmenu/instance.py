"""One TailMenu per Linux user, independent of install path or desktop session."""
import errno
import os
import socket


def acquire_instance(name: str = "tailscale-quick-menu"):
    # Linux abstract sockets provide an atomic, kernel-owned reservation. There
    # is no PID/lock file to go stale or unlink, even after SIGKILL. The UID,
    # rather than the Tailscale account or XDG paths, defines the instance.
    instance = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        instance.bind(f"\0{name}:{os.getuid()}")
    except OSError as exc:
        instance.close()
        if exc.errno == errno.EADDRINUSE:
            return None
        raise
    # Python sockets are non-inheritable: launching a browser/CLI must not keep
    # the reservation alive after TailMenu exits. No network port is opened.
    return instance
