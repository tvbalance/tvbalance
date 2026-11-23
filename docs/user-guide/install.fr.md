# Installer TVBalance

TVBalance fonctionne sur un petit ordinateur toujours allumé chez vous : l'appareil qui fait tourner Home Assistant, un
NAS ou un Raspberry Pi. Il doit être sur le même réseau que votre télé. Choisissez l'une des deux voies ci-dessous.

## Comme module complémentaire Home Assistant (recommandé)

Cela fonctionne avec Home Assistant OS et les installations Supervised, en amd64 et aarch64.

1. Dans Home Assistant, ouvrez **Paramètres → Modules complémentaires → Boutique des modules → ⋮ → Dépôts**.
2. Ajoutez `https://github.com/tvbalance/tvbalance`.
3. Installez **TVBalance**, démarrez-le et ouvrez le panneau **TVBalance** dans la barre latérale.
4. Suivez la configuration à l'écran. Voir [Premiers pas](getting-started.md).

Au démarrage, le module se signale à Home Assistant. Une notification **TVBalance** apparaît sous **Paramètres →
Appareils et services** : choisissez **Configurer** et confirmez. Il n'y a ni adresse ni jeton à saisir. Plus de détails
dans [Home Assistant](home-assistant.md).

Le module utilise le réseau de l'hôte pour pouvoir trouver et réveiller les télés. Toutes les données se trouvent dans
le dossier `/data` du module et font partie des sauvegardes de Home Assistant.

## Avec Docker

Une seule image multi-architecture (amd64 et arm64) couvre tout le reste :

```
docker run -d --name tvbalance --restart unless-stopped \
  --network host \
  -v tvbalance-data:/data \
  ghcr.io/tvbalance/tvbalance:latest
```

Ouvrez ensuite `http://<adresse-de-la-machine>:8765` dans un navigateur.

- **Réseau de l'hôte.** La recherche des télés et le Wake-on-LAN en ont besoin, et cela ne fonctionne ainsi que sous
  Linux. Avec Docker Desktop (Windows et macOS), utilisez plutôt `-p 8765:8765 -p 8766:8766` et ajoutez votre télé par
  son adresse, car elle ne peut pas être trouvée automatiquement.
- **Le volume de données.** `/data` contient `tvbalance.db` (vos télés, règles, historique d'utilisation et
  événements) et `secret.key` (la clé qui protège les identifiants enregistrés des télés). Conservez les deux
  ensemble et sauvegardez-les ensemble. Si la clé est perdue, les données restent, mais chaque télé doit être associée
  de nouveau.
- **Mises à jour.** Récupérez la nouvelle image et recréez le conteneur. La base de données est mise à niveau au
  démarrage.

### Réglages

Le moteur lit ses réglages dans des variables d'environnement. Les valeurs par défaut conviennent à la plupart des
foyers.

| Variable | Défaut | Signification |
| --- | --- | --- |
| `TVBALANCE_DATA_DIR` | `/data` | Où se trouvent la base de données et la clé |
| `TVBALANCE_PORT` | `8765` | Port HTTP |
| `TVBALANCE_HTTPS_PORT` | `8766` | Port HTTPS |
| `TVBALANCE_TLS` | `auto` | `auto` pour l'autorité locale intégrée, `off` pour désactiver HTTPS |
| `TVBALANCE_TLS_CERTFILE`, `TVBALANCE_TLS_KEYFILE` | non défini | Votre propre certificat et votre clé (à définir ensemble) |
| `TVBALANCE_TLS_NAMES` | non défini | Noms locaux supplémentaires pour le certificat automatique |

HTTPS est expliqué dans [HTTPS sur votre réseau](https.md).

### Home Assistant avec un moteur autonome

Créez un jeton d'API dans l'application web et installez l'intégration avec HACS. Les étapes sont dans
[Home Assistant](home-assistant.md).

## Les ports en bref

| Port | Protocole | Utilisé pour |
| --- | --- | --- |
| 8765 | HTTP | L'application web, l'Ingress de Home Assistant, le contrôle de santé |
| 8766 | HTTPS | L'application web et l'API sur votre réseau |

## Étape suivante

Ouvrez l'application web et suivez [Premiers pas](getting-started.md). Si quelque chose ne fonctionne pas, consultez le
[Dépannage](troubleshooting.md).
