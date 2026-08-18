#!/bin/sh
set -eu

APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/tailscale-quick-menu"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"

mkdir -p "$APP_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$AUTOSTART_DIR"
cp -R tailmenu "$APP_DIR/"
sed "s|@APP_DIR@|$APP_DIR|g" bin/tailscale-quick-menu > "$BIN_DIR/tailscale-quick-menu"
chmod 755 "$BIN_DIR/tailscale-quick-menu"
sed "s|@APP_DIR@|$APP_DIR|g" packaging/tailscale-quick-menu.desktop > "$DESKTOP_DIR/tailscale-quick-menu.desktop"
cp "$DESKTOP_DIR/tailscale-quick-menu.desktop" "$AUTOSTART_DIR/tailscale-quick-menu.desktop"

printf '%s\n' "TailMenu est installé. Lancez-le depuis vos applications."
