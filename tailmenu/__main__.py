#!/usr/bin/env python3
"""Shared entry point for the desktop launcher, autostart, and python -m."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tailmenu.instance import acquire_instance


def main():
    try:
        instance = acquire_instance()
    except OSError as exc:
        print(f"TailMenu : impossible de vérifier l’instance active : {exc}", file=sys.stderr)
        return 1
    if instance is None:
        print("TailMenu est déjà actif ; aucun nouvel exemplaire n’a été lancé.")
        return 0

    # Keep the lock until GTK exits, including startup failures. Importing GTK
    # only after acquiring it prevents duplicate launches from creating any UI.
    with instance:
        from tailmenu.app import run
        run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
