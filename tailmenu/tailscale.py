import json
import subprocess
from dataclasses import dataclass, field


@dataclass
class TailStatus:
    connected: bool = False
    account: str = ""
    ip: str = ""
    hostname: str = ""
    exit_nodes: list[tuple[str, str]] = field(default_factory=list)


def _run(args: list[str], privileged: bool = False) -> subprocess.CompletedProcess:
    command = (["pkexec"] if privileged else []) + ["tailscale", *args]
    return subprocess.run(command, text=True, capture_output=True, check=False)


def get_status() -> TailStatus:
    result = _run(["status", "--json"])
    if result.returncode != 0:
        return TailStatus()
    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        return TailStatus()
    self_node = data.get("Self") or {}
    user_id = str(self_node.get("UserID", ""))
    user_profile = (data.get("User") or {}).get(user_id, {})
    ips = self_node.get("TailscaleIPs") or []
    backend = data.get("BackendState", "")
    return TailStatus(
        connected=backend == "Running" and bool(self_node.get("Online", True)),
        account=user_profile.get("LoginName", ""),
        ip=next((ip for ip in ips if ":" not in ip), ips[0] if ips else ""),
        hostname=self_node.get("HostName", ""),
        exit_nodes=_exit_nodes(data),
    )


def _exit_nodes(data: dict) -> list[tuple[str, str]]:
    nodes = []
    for peer in (data.get("Peer") or {}).values():
        if not peer.get("ExitNodeOption"):
            continue
        ips = peer.get("TailscaleIPs") or []
        ipv4 = next((ip for ip in ips if ":" not in ip), "")
        if ipv4:
            nodes.append((peer.get("DNSName", "").rstrip(".") or peer.get("HostName", ipv4), ipv4))
    return sorted(nodes, key=lambda node: node[0].lower())


def action(*args: str) -> tuple[bool, str]:
    result = _run(list(args), privileged=True)
    return result.returncode == 0, (result.stderr or result.stdout).strip()
