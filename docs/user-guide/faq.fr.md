# Questions fréquentes

## TVBalance a-t-il besoin d'un compte ou d'internet ?
Non. Il fonctionne sur votre propre réseau et parle directement à la télé. Il n'y a ni compte cloud ni télémétrie. La
licence Pro est une clé signée vérifiée sur votre appareil, donc elle n'a pas besoin de connexion non plus.

## Où sont mes données ?
Dans le dossier de données du moteur (`/data` dans le module complémentaire et dans Docker) : la base `tvbalance.db` avec
les télés, les règles, l'historique d'utilisation et les événements, et `secret.key`, qui protège les identifiants
enregistrés des télés. Les données du module font partie des sauvegardes de Home Assistant. Gardez la base et la clé
ensemble.

## Quelles télés sont prises en charge ?
LG webOS 4 et plus récent est pris en charge et vérifié sur du matériel réel. Roku, Google/Android TV et Samsung Tizen
sont prévus et pas encore utilisables. Chaque marque peut faire des choses différentes, et l'application ne propose que
ce que la télé sait réellement faire. Voir [LG webOS](tv-lg-webos.md) pour ce que prend en charge une LG.

## Cela fonctionne-t-il sans Home Assistant ?
Oui. L'application web fonctionne seule, avec Docker ou le module complémentaire. Home Assistant ajoute des entités, des
services, des événements et des blueprints pour les automatisations. Voir [Installer](install.md) et
[Home Assistant](home-assistant.md).

## Qu'est-ce qui est gratuit et qu'est-ce qui est Pro ?
Une télé avec toutes les règles de base (horaires, budgets quotidiens, blocage d'applications, d'entrées et de chaînes,
actions parentales, notifications, Home Assistant) est gratuite. Pro est une licence unique pour le foyer qui permet plus
de télés, des profils et un calendrier, des budgets avancés, un long historique et des rapports hebdomadaires. Voir
[TVBalance Pro](pro.md).

## Que se passe-t-il si ma licence Pro expire ?
Rien n'est supprimé. Les réglages Pro restent enregistrés et ne sont plus appliqués : les télés au-delà de la première ne
sont plus surveillées, et les règles reviennent aux règles de base. Ajoutez une licence valide et elles s'appliquent de
nouveau.

## Mon enfant peut-il le contourner ?
TVBalance agit sur la télé, donc un téléphone ou une autre télécommande n'y change rien. C'est un outil familial, pas un
verrou : un enfant qui accède au menu de réglages de la télé peut toujours la débrancher ou changer le réseau. Utilisez
le PIN de la télé et, sur les appareils partagés, un PIN pour les commandes parentales de TVBalance. Se connecter pour
modifier les règles demande le mot de passe administrateur.

## Puis-je utiliser plusieurs télés ?
Oui, avec [Pro](pro.md). Chaque télé suit un jeu de règles, et plusieurs télés peuvent partager le même.

## Quelles langues sont disponibles ?
Anglais, italien, allemand, français et espagnol. L'application web suit votre navigateur ou Home Assistant, et vous
pouvez la changer dans **Réglages → Général**. Cette documentation existe dans les mêmes cinq langues.

## Cela fonctionne-t-il en HTTPS ?
Oui. HTTPS est activé par défaut, avec un certificat d'une autorité locale à laquelle vos appareils font confiance une
fois. Vous pouvez aussi utiliser votre propre certificat. Voir [HTTPS sur votre réseau](https.md).

## Comment mettre à jour ?
Avec le module complémentaire, mettez-le à jour depuis la boutique des modules. Avec Docker, récupérez la nouvelle image
et recréez le conteneur. Vos données et réglages sont conservés et la base est mise à niveau au démarrage.

## Comment signaler un problème ou demander une marque de télé ?
Ouvrez un ticket sur <https://github.com/tvbalance/tvbalance/issues>. Joignez le téléchargement de diagnostic et ne
publiez ni jetons ni clés de licence. Les développeurs peuvent ajouter eux-mêmes une marque avec un paquet adaptateur :
voir [Écrire un adaptateur](../developers/adapters.md).
