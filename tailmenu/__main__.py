#!/usr/bin/env python3
import os
import sys
import webbrowser
from threading import Thread

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AyatanaAppIndicator3", "0.1")
from gi.repository import AyatanaAppIndicator3 as AppIndicator, Gdk, GLib, Gtk

from tailmenu import tailscale
from tailmenu.controller import Controller


class TailMenu:
    def __init__(self):
        self.indicator = AppIndicator.Indicator.new(
            "tailscale-quick-menu", "network-vpn-symbolic", AppIndicator.IndicatorCategory.SYSTEM_SERVICES
        )
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self.controller = Controller(GLib.idle_add, self.render, self.show_error, self.open_login)
        self.render()
        self.controller.refresh()
        GLib.timeout_add_seconds(3, self.controller.refresh)

    @property
    def status(self):
        return self.controller.status

    def item(self, label, callback=None, sensitive=True):
        item = Gtk.MenuItem(label=label)
        item.set_sensitive(sensitive)
        if callback:
            item.connect("activate", callback)
        item.show()
        return item

    def render(self):
        menu = Gtk.Menu()
        state = self.status.label
        menu.append(self.item(f"● {state}", sensitive=False))
        if self.controller.busy:
            menu.append(self.item("Action en cours…", sensitive=False))
        if self.status.error:
            menu.append(self.item("Voir l’erreur…", lambda *_: self.show_error(self.status.error)))
        if self.status.auth_url and not self.status.connected:
            menu.append(self.item("Ouvrir la page de connexion…", lambda *_: self.open_login(self.status.auth_url)))
        account_label = f"Compte : {self.status.account}" if self.status.account else "Compte indisponible"
        menu.append(self.item(account_label, sensitive=False))
        ip_label = f"Adresse : {self.status.ip}" if self.status.ip else "Adresse indisponible"
        menu.append(self.item(ip_label, self.copy_ip, bool(self.status.ip)))
        menu.append(Gtk.SeparatorMenuItem())
        if self.status.connected:
            menu.append(self.item("Se déconnecter temporairement", lambda *_: self.run_action("down"), not self.controller.busy))
        else:
            menu.append(self.item("Se connecter", lambda *_: self.run_action("up"), not self.controller.busy))
        menu.append(self.item("Changer de compte…", self.change_account, not self.controller.busy))
        exit_item = self.item("Serveur de sortie (Exit Node)", sensitive=not self.controller.busy and self.status.connected)
        exit_menu = Gtk.Menu()
        exit_menu.append(self.item("Aucun", lambda *_: self.run_action("set", "--exit-node=")))
        for name, ip in self.status.exit_nodes:
            exit_menu.append(self.item(name, lambda _item, node_ip=ip: self.run_action("set", f"--exit-node={node_ip}")))
        exit_item.set_submenu(exit_menu)
        menu.append(exit_item)
        menu.append(Gtk.SeparatorMenuItem())
        menu.append(self.item("Administration Tailscale", lambda *_: webbrowser.open("https://login.tailscale.com/admin/machines")))
        menu.append(self.item("Actualiser", self.controller.refresh))
        menu.append(self.item("Quitter TailMenu", lambda *_: Gtk.main_quit()))
        menu.show_all()
        self.indicator.set_menu(menu)
        self.indicator.set_icon_full("network-vpn-symbolic" if self.status.connected else "network-vpn-disconnected-symbolic", state)
        return True

    def copy_ip(self, *_args):
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(self.status.ip, -1)

    def run_action(self, *args):
        self.controller.start(args)

    def show_error(self, message):
        dialog = Gtk.MessageDialog(message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE, text="Action impossible")
        dialog.format_secondary_text(message)
        dialog.connect("response", lambda widget, *_: widget.destroy())
        dialog.show_all()
        return False

    def open_login(self, url):
        url = tailscale.login_url(url)
        if not url:
            return

        def open_browser():
            try:
                opened = webbrowser.open(url)
            except Exception:
                opened = False
            if not opened:
                GLib.idle_add(self.show_error, "Impossible d’ouvrir le navigateur. Réessayez avec « Ouvrir la page de connexion… » dans le menu.")

        Thread(target=open_browser, daemon=True).start()

    def change_account(self, *_args):
        self.controller.start(("logout",), ("up",))


if __name__ == "__main__":
    TailMenu()
    Gtk.main()
