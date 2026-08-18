#!/bin/sh
set -eu

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
rm -rf "$DATA_HOME/tailscale-quick-menu"
rm -f "$HOME/.local/bin/tailscale-quick-menu"
rm -f "$DATA_HOME/applications/tailscale-quick-menu.desktop"
rm -f "$CONFIG_HOME/autostart/tailscale-quick-menu.desktop"
printf '%s\n' "TailMenu a été désinstallé."
