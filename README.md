# TailMenu

Un petit menu Tailscale en français pour la barre système d'Ubuntu/GNOME.

## Fonctions

- état Connecté / Déconnecté et adresse IPv4 Tailscale ;
- copie de l'adresse IP en un clic ;
- connexion et déconnexion temporaire ;
- déconnexion du compte puis connexion à un autre compte ;
- choix ou retrait d'un Exit Node ;
- accès direct à la console d'administration Tailscale ;
- rafraîchissement automatique toutes les 10 secondes.

## Installation sur Ubuntu

Tailscale doit déjà être installé.

```bash
sudo apt update
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1
git clone https://github.com/eNric0-hash/tailscale-quick-menu.git
cd tailscale-quick-menu
./install.sh
```

Lance ensuite **TailMenu** depuis la liste des applications. Sur GNOME, si
l'icône n'apparaît pas, installe/active l'extension « AppIndicator and KStatusNotifierItem Support ».

Les opérations privilégiées passent par `pkexec` : Ubuntu affiche donc une
demande d'autorisation normale lorsque c'est nécessaire.

## Développement

```bash
python3 -m unittest discover -s tests -v
python3 -m tailmenu
```

## Désinstallation

```bash
./uninstall.sh
```

