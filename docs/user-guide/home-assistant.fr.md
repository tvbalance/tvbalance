# Home Assistant

TVBalance fournit sa propre intégration, qui montre chaque télé comme un appareil dans Home Assistant, vous envoie des
événements et permet aux automatisations d'accorder ou de retirer du temps de télé.

## Configuration

### Avec le module complémentaire (recommandé)

Installez le module complémentaire TVBalance et démarrez-le. Home Assistant affiche une notification **TVBalance** sous
**Paramètres → Appareils et services** : choisissez **Configurer** et confirmez. Le module crée et conserve le jeton
d'API pour vous ; si vous le révoquez, redémarrez le module et Home Assistant adopte le nouveau.

### Avec un moteur autonome

1. Dans l'application web de TVBalance, ouvrez **Réglages → Jetons d'API** et créez un jeton avec les portées
   **lecture** et **contrôle**. N'ajoutez **admin** que si vous voulez le service `tvbalance.set_monitoring`. Le secret
   n'est affiché qu'une fois.
2. Installez l'intégration avec HACS (ajoutez `https://github.com/tvbalance/tvbalance-ha` comme dépôt personnalisé,
   catégorie Intégration) ou copiez `custom_components/tvbalance` dans le dossier `config/custom_components` de Home
   Assistant. Redémarrez Home Assistant.
3. **Paramètres → Appareils et services → Ajouter une intégration → TVBalance**. Saisissez l'adresse du moteur et le
   jeton.

Pour HTTPS, saisissez une adresse `https://` (port 8766 par défaut). Si le certificat n'est pas encore approuvé, la
configuration affiche l'empreinte de l'autorité locale du moteur : comparez-la à **Réglages → Connexion sécurisée**
dans l'application web de TVBalance et confirmez. Home Assistant n'accepte alors que cette autorité pour ce moteur. Si
elle change (un nouveau certificat a été créé), Home Assistant demande de confirmer à nouveau. Voir https.md.

Si le jeton est révoqué ou expire, Home Assistant en demande un nouveau (une réparation apparaît ; choisissez
**Reconfigurer**). Rien d'autre n'est à refaire.

## Ce que vous obtenez pour chaque télé

| Entité | Signification |
| --- | --- |
| État (capteur) | `watching`, `standby`, `off`, `unreachable`, `needs_pairing` ou `not_monitored` |
| Application, Émission (capteurs) | Ce qui est à l'écran. L'entrée et la chaîne existent aussi, désactivées par défaut |
| Profil (capteur) | Le nom du profil qui s'applique à cette télé, inconnu s'il n'y en a pas |
| Regardé aujourd'hui, Temps restant (capteurs) | Minutes ; Temps restant est inconnu si la télé n'a pas de budget quotidien |
| Bloquée (capteur binaire) | Actif tant que l'application des règles bloque la télé ; l'attribut `reason` donne la raison |
| Connectée, À réassocier (capteurs binaires) | État de la connexion |
| Pause (bouton) | Suspend l'application des règles pendant 30 minutes. Sans danger pour tout le monde |
| Activité (entité d'événement) | Se déclenche à chaque événement TVBalance |

Le moteur envoie les changements en direct, donc les états se mettent à jour en moins d'une seconde. Si le flux
s'interrompt, Home Assistant se reconnecte tout seul et continue d'interroger toutes les 30 secondes.

## Services (administrateurs uniquement)

Tout ce qui donne plus de temps de télé ou change l'application des règles est réservé aux administrateurs de Home
Assistant, pour qu'un enfant devant un tableau de bord ne puisse pas l'appeler. Les automatisations et les scripts le
peuvent. Chaque service prend un `device_id` (la télé).

| Service | Champs |
| --- | --- |
| `tvbalance.bonus` | `minutes` (1–240) |
| `tvbalance.allow` | `minutes` (1–1440) ou `until_midnight` |
| `tvbalance.block` | `minutes` (1–1440) ou `until_midnight` |
| `tvbalance.pause` | `minutes` (1–1440) |
| `tvbalance.clear_override` | aucun |
| `tvbalance.set_monitoring` | `enabled` ; demande un jeton avec la portée admin |

Les services de profil concernent tout le foyer, pas une télé, et demandent l'offre Pro :

| Service | Champs |
| --- | --- |
| `tvbalance.activate_profile` | `policy_id`, `minutes` (1–1440) ou `until_midnight`, `excluded_device_ids` facultatif |
| `tvbalance.stop_profile` | aucun |

`allow`, `block` et `activate_profile` demandent exactement l'un de `minutes` ou `until_midnight`. Un PIN ne fait jamais
partie d'un appel de service.

## Événements

Chaque événement du moteur est aussi émis comme `tvbalance_event` sur le bus de Home Assistant, avec `device_id`,
`tv_id`, `type` et `payload`. Types : `time_warning` (`minutes_left`, `limit`), `blocked` (`reason`), `redirected`
(`action`), `powered_off`, `enforcement_paused`, `enforcement_unavailable` (`reason`), `tv_unreachable`,
`tv_reachable`, `pairing_lost`, `tv_paired`, `profile_started` (`name`, `until`, `source`), `profile_ended` (`name`),
`weekly_report` (`first`, `last`, `total_seconds`, `blocks`, `top`).

## Blueprints

Ils se trouvent dans `blueprints/automation/tvbalance/` ; copiez-les dans `config/blueprints/automation/tvbalance/`.

- **warning_light** : fait clignoter une lumière quand il reste N minutes ou moins à une télé.
- **notify_parent** : envoie une notification pour les événements choisis.
- **button_bonus** : accorde des minutes bonus quand un bouton physique est pressé.
- **calendar_profile** : active un jeu de règles pour le foyer pendant qu'un événement du calendrier de Home Assistant
  est en cours, et le désactive à sa fin (Pro).
