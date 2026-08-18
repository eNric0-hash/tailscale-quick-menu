#!/usr/bin/env python3
import os
import sys
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AyatanaAppIndicator3", "0.1")
from gi.repository import AyatanaAppIndicator3 as AppIndicator, GLib, Gtk

from tailmenu import tailscale


class TailMenu:
    def __init__(self):
        self.indicator = AppIndicator.Indicator.new(
            "tailscale-quick-menu", "network-vpn-symbolic", AppIndicator.IndicatorCategory.SYSTEM_SERVICES
        )
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self.status = tailscale.TailStatus()
        self.refresh()
        GLib.timeout_add_seconds(10, self.refresh)

    def item(self, label, callback=None, sensitive=True):
        item = Gtk.MenuItem(label=label)
        item.set_sensitive(sensitive)
        if callback:
            item.connect("activate", callback)
        item.show()
        return item

    def refresh(self, *_args):
        self.status = tailscale.get_status()
        menu = Gtk.Menu()
        state = "Connecté" if self.status.connected else "Déconnecté"
        menu.append(self.item(f"● {state}", sensitive=False))
        account_label = f"Compte : {self.status.account}" if self.status.account else "Compte indisponible"
        menu.append(self.item(account_label, sensitive=False))
        ip_label = f"Adresse : {self.status.ip}" if self.status.ip else "Adresse indisponible"
        menu.append(self.item(ip_label, self.copy_ip, bool(self.status.ip)))
        menu.append(Gtk.SeparatorMenuItem())
        if self.status.connected:
            menu.append(self.item("Se déconnecter temporairement", lambda *_: self.run_action("down")))
        else:
            menu.append(self.item("Se connecter", lambda *_: self.run_action("up")))
        menu.append(self.item("Changer de compte…", self.change_account))
        exit_item = self.item("Serveur de sortie (Exit Node)")
        exit_menu = Gtk.Menu()
        exit_menu.append(self.item("Aucun", lambda *_: self.run_action("set", "--exit-node=")))
        for name, ip in self.status.exit_nodes:
            exit_menu.append(self.item(name, lambda _item, node_ip=ip: self.run_action("set", f"--exit-node={node_ip}")))
        exit_item.set_submenu(exit_menu)
        menu.append(exit_item)
        menu.append(Gtk.SeparatorMenuItem())
        menu.append(self.item("Administration Tailscale", lambda *_: webbrowser.open("https://login.tailscale.com/admin/machines")))
        menu.append(self.item("Actualiser", self.refresh))
        menu.append(self.item("Quitter TailMenu", lambda *_: Gtk.main_quit()))
        menu.show_all()
        self.indicator.set_menu(menu)
        self.indicator.set_icon_full("network-vpn-symbolic" if self.status.connected else "network-vpn-disconnected-symbolic", state)
        return True

    def copy_ip(self, *_args):
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(self.status.ip, -1)

    def run_action(self, *args):
        ok, message = tailscale.action(*args)
        if not ok and message:
            dialog = Gtk.MessageDialog(message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE, text="Action impossible")
            dialog.format_secondary_text(message)
            dialog.run()
            dialog.destroy()
        self.refresh()

    def change_account(self, *_args):
        self.run_action("logout")
        self.run_action("up")


if __name__ == "__main__":
    from gi.repository import Gdk
    TailMenu()
    Gtk.main()
