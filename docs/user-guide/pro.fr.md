# TVBalance Pro

TVBalance est gratuit pour une télé. Une **licence Pro**, achetée une fois pour tout le foyer, lève la limite et débloque
les fonctions avancées à mesure qu'elles arrivent.

| | Free | Pro |
| --- | --- | --- |
| Télés surveillées | 1 | Illimité |
| Profils et calendrier | Non | Oui |
| Budgets avancés (par jour de la semaine, groupes d'applications, report) | Non | Oui |
| Historique au-delà de 7 jours, usage par application, rapport hebdomadaire | Non | Oui |
| Règles, budgets de temps, actions parentales, notifications, Home Assistant | Oui | Oui |

La licence est une clé que vous collez dans l'application. Elle est vérifiée sur votre propre appareil par une
signature : elle n'a donc pas besoin de connexion internet, et rien sur vous n'est envoyé nulle part.

## Profils et calendrier

Un **profil** est un jeu de règles que vous activez d'un coup pour tout le foyer, par exemple « Vacances » ou « Week-end
chez les grands-parents ». Tant qu'il est actif, chaque télé le suit au lieu de son propre jeu de règles, sauf les télés
que vous écartez (disons celle des parents).

- **À la main :** dans **Règles**, appuyez sur *Activer comme profil* pour un jeu, choisissez la durée (de 30 minutes à
  4 heures, ou jusqu'à minuit) et les télés à écarter. Le tableau de bord montre le profil actif avec un bouton *Arrêter
  le profil*.
- **Par le calendrier :** dans **Règles > Calendrier**, ajoutez des entrées qui activent un jeu de règles toutes seules,
  soit chaque semaine à des jours et heures choisis (une plage qui se termine avant son début passe minuit), soit entre
  deux dates.
- **Depuis Home Assistant :** les services `tvbalance.activate_profile` et `tvbalance.stop_profile` et le blueprint
  « calendar ».

Quand plusieurs s'appliquent, le profil manuel le plus récent l'emporte, puis une entrée datée du calendrier, puis une
entrée hebdomadaire, puis le jeu de règles propre à la télé. Arrêter un profil ou le laisser expirer ramène chaque télé
à ses propres règles.

Vous pouvez configurer profils et calendrier avec n'importe quelle offre ; ils sont enregistrés mais appliqués
seulement avec une licence Pro, et les écrans le disent. Rien n'est perdu si une licence se termine.

## Budgets avancés

Le budget quotidien d'un jeu de règles peut être affiné dans **Règles > Horaires** :

- **Budget par jour de la semaine :** un nombre de minutes différent pour chaque jour, par exemple plus le samedi. Un
  jour laissé vide utilise le budget quotidien.
- **Groupes d'applications :** un groupe d'applications, comme « Jeux », qui partagent une même allocation quotidienne.
  Quand le temps du groupe est épuisé, ses applications sont bloquées alors que tout le reste reste disponible, et un
  avertissement apparaît avant la fin. Choisissez les applications dans la liste lue sur la télé.
- **Reporter le temps non utilisé :** les minutes non utilisées hier s'ajoutent à aujourd'hui, jusqu'à un maximum que
  vous choisissez. Les minutes reportées ne s'accumulent jamais d'un jour à l'autre.

Ils peuvent être configurés avec n'importe quelle offre et sont enregistrés dans tous les cas, mais ne sont appliqués
qu'avec une licence Pro ; en Free, le simple budget quotidien s'applique. Rien n'est perdu si une licence se termine.

## Historique et rapport hebdomadaire

**Activité** peut afficher les 7, 30, 90 ou 365 derniers jours, avec une barre par jour et les applications, entrées et
chaînes les plus regardées de chaque télé. En offre Free, l'historique s'arrête à 7 jours et un avis l'indique.

Chaque lundi à 8 h (heure du foyer), le **rapport hebdomadaire** de la semaine précédente est prêt : combien de temps
chaque télé a été regardée, quels jours, les applications principales et combien de fois un contenu a été bloqué. Il
apparaît dans Activité et peut aussi arriver en notification : activez « Un rapport hebdomadaire le lundi » pour un
appareil dans **Réglages > Notifications** (désactivé par défaut). Home Assistant reçoit un événement `weekly_report`.

## Obtenir et activer une licence
1. Dans **Réglages → TVBalance Pro**, choisissez **Acheter Pro** (visible quand la page d'achat est configurée).
2. Après le paiement, vous recevez une clé de licence : une longue ligne de lettres et de chiffres avec un point au
   milieu.
3. Collez-la dans **Clé de licence** et choisissez **Activer**. Seul l'administrateur voit cette carte.

La carte indique ensuite l'offre, à qui la licence est destinée et la date d'expiration, s'il y en a une. La plupart des
licences n'expirent jamais.

## Ce qui se passe en offre Free avec plusieurs télés
Vous pouvez toujours ajouter et configurer autant de télés que vous voulez. En offre Free, seule la **plus ancienne télé
activée** est surveillée ; les autres gardent leurs réglages mais ne sont pas surveillées et sont marquées **Nécessite
Pro**. Désactivez la plus ancienne télé et la suivante prend sa place.

## Expiration et retrait
Rien n'est supprimé quand une licence expire ou que vous la retirez. Le foyer repasse simplement à l'offre Free, et les
télés supplémentaires ne sont plus surveillées jusqu'à ce qu'une licence soit de nouveau active. Une clé enregistrée qui
cesse d'être valide (par exemple après une rotation de clés) est traitée de la même façon, et la carte l'indique.

Le retrait de la licence se fait dans **Réglages → TVBalance Pro → Retirer la licence**.
