# TailMenu

Un petit menu Tailscale en français pour la barre système d'Ubuntu/GNOME.

## Fonctions

- état Connecté / Déconnecté et adresse IPv4 Tailscale ;
- copie de l'adresse IP en un clic ;
- connexion et déconnexion temporaire ;
- déconnexion du compte puis connexion à un autre compte dans le navigateur ;
- choix ou retrait d'un Exit Node ;
- accès direct à la console d'administration Tailscale ;
- rafraîchissement automatique toutes les 3 secondes, même pendant une connexion ;
- états d’authentification et erreurs visibles, sans bloquer le menu.

## Installation sur Ubuntu

Tailscale doit déjà être installé.

```bash
sudo apt update
sudo apt install git python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1
git clone https://github.com/eNric0-hash/tailscale-quick-menu.git
cd tailscale-quick-menu
./install.sh
```

Lance ensuite **TailMenu** depuis la liste des applications. Sur GNOME, si
l'icône n'apparaît pas, installe/active l'extension « AppIndicator and KStatusNotifierItem Support ».

Les opérations privilégiées passent par `pkexec` : Ubuntu affiche donc une
demande d'autorisation normale lorsque c'est nécessaire.

## Connexion et changement de compte

Clique sur **Se connecter** ou **Changer de compte…**, puis accepte la demande
d’autorisation Ubuntu. Le navigateur ouvre la connexion Tailscale lorsque le
service fournit son lien. Termine l’authentification dans le navigateur ; le menu
actualise ensuite l’état automatiquement. Si nécessaire, utilise **Ouvrir la page
de connexion…** pour rouvrir le lien.

Le changement de compte déconnecte d’abord le compte actuel. Si cette opération
est refusée ou échoue, la connexion suivante n’est pas lancée. Pendant une action,
les autres commandes réseau sont désactivées, mais l’état continue à être lu.
L’attente de connexion est limitée à trois minutes ; en cas d’erreur, le menu
affiche le détail et permet de réessayer. Une demande d’approbation de l’appareil
doit être validée par l’administrateur du réseau Tailscale.

## Mise à jour

Quitte l’ancienne instance de TailMenu puis, dans le dossier du dépôt :

```bash
git pull --ff-only
./install.sh
```

Relance **TailMenu** depuis les applications. Si l’ancienne version est figée,
termine uniquement son processus via le Moniteur système, ou ferme puis rouvre
ta session Ubuntu. Mettre à jour les fichiers ne remplace pas le processus déjà
en cours d’exécution.

## Développement

```bash
python3 -m unittest discover -s tests -v
python3 -m tailmenu
```

## Désinstallation

```bash
./uninstall.sh
```
