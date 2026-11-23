# Dépannage

Commencez par le tableau de bord : chaque carte de télé indique si la télé est allumée, injoignable ou **À réassocier**.
**Activité** montre les derniers événements, comme les problèmes de connexion, en termes simples.

## La télé n'est pas trouvée
- Vérifiez que la télé est allumée et sur le même réseau que TVBalance, pas sur un réseau invité.
- Certains routeurs bloquent les messages de découverte entre appareils. Choisissez la marque sous *Saisir l'adresse*
  dans l'assistant et tapez l'adresse IP de la télé, que vous trouvez dans ses réglages réseau.
- Avec Docker sous Windows ou macOS, la découverte ne peut pas fonctionner car le conteneur est derrière un réseau
  virtuel. Saisissez l'adresse à la main. Voir [Installer](install.md).
- Donnez à la télé une adresse fixe dans votre routeur (une réservation DHCP), pour que l'adresse saisie reste valable.
- Pour les télés LG, vérifiez les réglages dans [LG webOS](tv-lg-webos.md).

## L'association ne se termine pas
- Gardez la télécommande à portée de main et acceptez la demande sur la télé dans les trois minutes. La télé ne
  l'affiche que si elle est allumée.
- Si vous avez appuyé sur **Non** ou que rien ne s'est passé, utilisez **Réessayer** dans l'assistant.
- Assurez-vous que la télé n'affiche pas une autre invite plein écran ni un économiseur d'écran.

## La carte indique « À réassocier »
La télé a oublié la clé que détient TVBalance, par exemple après une réinitialisation d'usine ou une mise à jour du
logiciel. Ouvrez **Associer de nouveau** sur la carte et acceptez la demande sur la télé une fois de plus. Les règles,
l'historique et les réglages sont conservés. Si Web Push est activé, vous recevez aussi une notification.

## La télé est « injoignable »
TVBalance ne peut pas se connecter à la télé, ce qui est normal si elle est débranchée. Si cela arrive alors qu'elle est
allumée :

- Vérifiez l'adresse de la télé dans votre routeur. Si elle a changé, retirez la télé et ajoutez-la de nouveau avec sa
  nouvelle adresse, ou donnez-lui une adresse fixe.
- Vérifiez que les fonctions réseau de la télé sont toujours activées (pour LG, voir [LG webOS](tv-lg-webos.md)).
- Redémarrez complètement la télé (débranchez-la une minute). Certaines télés cessent de répondre après une longue
  durée de fonctionnement.

## Une règle ne semble pas s'appliquer
- Vérifiez que la télé a la surveillance activée (page de détails de la télé) et qu'elle suit le jeu de règles que vous
  avez modifié.
- Sur les télés LG avec **Quick Start+**, une télé écran éteint signale la veille, donc le budget quotidien ne s'écoule
  pas. C'est normal. Voir les limites dans [LG webOS](tv-lg-webos.md).
- Un **Autoriser** ou **Bloquer** manuel prend le dessus sur les règles jusqu'à sa fin. Utilisez **Annuler le forçage**
  sur la carte.
- Les profils, le calendrier et les budgets avancés sont enregistrés avec toutes les offres mais appliqués seulement avec
  [Pro](pro.md). Les écrans le disent.
- Les horaires suivent le fuseau choisi à la configuration, pas l'horloge de la télé. Vérifiez-le dans **Réglages →
  Général**.

## Le navigateur avertit que la connexion n'est pas privée
L'adresse sécurisée utilise un certificat d'une petite autorité créée par TVBalance. Votre appareil doit lui faire
confiance une fois. Suivez [HTTPS sur votre réseau](https.md) : téléchargez le certificat dans **Réglages → Connexion
sécurisée**, installez-le et comparez l'empreinte. Firefox a sa propre liste, importez-le donc aussi là.

## Pas de notifications sur le téléphone
Les navigateurs n'autorisent les notifications push que sur une connexion sécurisée.

- Ouvrez l'application web via Home Assistant en HTTPS, ou via l'adresse sécurisée de TVBalance, pas via une simple
  adresse `http://`. La carte dans **Réglages → Notifications** renvoie vers l'adresse sécurisée quand elle existe.
- Sur iPhone et iPad, ajoutez d'abord TVBalance à l'écran d'accueil et activez les notifications depuis cette icône.
- Envoyez un test depuis la même carte. S'il n'arrive pas, autorisez les notifications pour le site ou l'application
  dans les réglages du téléphone.

## Home Assistant ne trouve pas TVBalance
- Avec le module complémentaire, redémarrez-le et cherchez la notification **TVBalance** sous **Paramètres → Appareils
  et services**.
- Si vous avez révoqué le jeton « Home Assistant (Add-on) » dans **Réglages → Jetons d'API**, redémarrez le module : il
  en crée un nouveau.
- Avec un moteur autonome, vérifiez l'adresse, le port et que le jeton a les portées **lecture** et **contrôle**. Voir
  [Home Assistant](home-assistant.md).

## Un PIN est refusé
Après cinq PIN erronés, la connexion par PIN se verrouille un moment. Attendez, ou connectez-vous avec le mot de passe
administrateur et changez le PIN dans **Réglages → Sécurité**.

## Mot de passe administrateur oublié
TVBalance n'a pas encore de réinitialisation du mot de passe, car rien n'est envoyé hors de chez vous. Si un navigateur
est encore connecté, vous pouvez changer le mot de passe dans **Réglages → Sécurité**. Sinon, la seule solution
aujourd'hui est de repartir d'un dossier de données vide : les règles, l'historique et les clés enregistrées des télés
sont perdus et chaque télé doit être associée de nouveau. Restaurez une sauvegarde faite avant la perte du mot de passe
si vous en avez une.

## Toujours bloqué
Ouvrez un ticket sur <https://github.com/tvbalance/tvbalance/issues> et joignez le téléchargement de diagnostic. Ne
publiez ni jetons, ni clés de licence, ni le contenu du dossier de données.
