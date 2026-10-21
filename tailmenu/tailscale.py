import json
import subprocess
from dataclasses import dataclass, field
from urllib.parse import urlsplit


@dataclass
class TailStatus:
    connected: bool = False
    account: str = ""
    ip: str = ""
    hostname: str = ""
    exit_nodes: list[tuple[str, str]] = field(default_factory=list)
    backend: str = ""
    auth_url: str = ""
    error: str = ""

    @property
    def label(self) -> str:
        if self.error:
            return "État indisponible"
        if self.connected:
            return "Connecté"
        return {
            "NeedsLogin": "Connexion au compte requise",
            "NeedsMachineAuth": "Approbation de l’appareil requise",
            "Starting": "Connexion en cours…",
            "Running": "Connexion au réseau indisponible",
        }.get(self.backend, "Déconnecté")


def _run(args: list[str], privileged: bool = False, timeout: int = 8) -> subprocess.CompletedProcess:
    command = (["pkexec"] if privileged else []) + ["tailscale", *args]
    return subprocess.run(command, text=True, capture_output=True, check=False, timeout=timeout)


def get_status() -> TailStatus:
    try:
        result = _run(["status", "--json"])
    except (OSError, subprocess.TimeoutExpired) as exc:
        return TailStatus(error=f"Tailscale ne répond pas : {exc}")
    if result.returncode != 0:
        return TailStatus(error=(result.stderr or "Service Tailscale inaccessible").strip())
    try:
        data = json.loads(result.stdout)
    except (json.JSONDecodeError, TypeError):
        return TailStatus(error="Réponse Tailscale illisible")
    if not isinstance(data, dict):
        return TailStatus(error="Réponse Tailscale invalide")
    self_node = data.get("Self") or {}
    user_id = str(self_node.get("UserID", ""))
    user_profile = (data.get("User") or {}).get(user_id, {})
    ips = self_node.get("TailscaleIPs") or []
    backend = data.get("BackendState", "")
    return TailStatus(
        connected=backend == "Running" and self_node.get("Online") is True,
        account=user_profile.get("LoginName", ""),
        ip=next((ip for ip in ips if ":" not in ip), ips[0] if ips else ""),
        hostname=self_node.get("HostName", ""),
        exit_nodes=_exit_nodes(data),
        backend=backend,
        auth_url=login_url(data.get("AuthURL")),
    )


def login_url(value) -> str:
    # Only open web links supplied by the local daemon, never file/command URLs.
    if not isinstance(value, str):
        return ""
    try:
        parsed = urlsplit(value)
        return value if parsed.scheme in ("https", "http") and parsed.hostname and not parsed.username else ""
    except ValueError:
        return ""


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
    command = list(args)
    if command and command[0] == "up":
        command.append("--timeout=180s")
    try:
        result = _run(command, privileged=True, timeout=210)
    except subprocess.TimeoutExpired:
        return False, "Délai dépassé. Vérifiez l’autorisation système et terminez la connexion dans le navigateur, puis réessayez."
    except OSError as exc:
        return False, f"Impossible de lancer Tailscale : {exc}"
    message = (result.stderr or result.stdout).strip()
    if result.returncode in (126, 127) and not message:
        message = "Autorisation système annulée ou refusée."
    if result.returncode == 0:
        return True, message
    return False, message or f"La commande a échoué (code {result.returncode})."
