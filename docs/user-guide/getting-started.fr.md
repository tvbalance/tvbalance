# Premiers pas

De l'installation toute neuve à une télé qui suit vos règles, il faut environ cinq minutes. Il vous faut TVBalance
[installé](install.md) et votre télé allumée, sur le même réseau.

## 1. Ouvrir l'application web
Ouvrez le panneau **TVBalance** dans Home Assistant, ou `http://<adresse-de-la-machine>:8765` si vous utilisez Docker.
La première visite lance la configuration.

## 2. Configurer le foyer
L'application demande trois choses :

1. **Un mot de passe** pour l'administrateur, d'au moins 10 caractères. Gardez-le en lieu sûr.
2. **La langue et le fuseau horaire.** Les horaires et les limites quotidiennes suivent ce fuseau.
3. **Un premier jeu de règles.** Partez de « Jours d'école » ou d'un jeu vide. Tout peut être modifié ensuite.

## 3. Ajouter votre télé
Choisissez **Ajouter une télé**. L'assistant explore votre réseau et liste les télés trouvées. Si la vôtre n'y est pas,
saisissez son adresse à la main. Suivez les étapes de votre marque, par exemple [LG webOS](tv-lg-webos.md) : la télé
vous demande d'accepter le nouvel appareil, ce que vous faites une fois avec la télécommande.

Donnez un nom à la télé et choisissez le jeu de règles qu'elle doit suivre. C'est tout : la carte de la télé dans le
tableau de bord indique maintenant ce qui est en cours, combien de minutes ont été regardées et combien il en reste.

## 4. Vérifier que cela fonctionne
- Ouvrez une application que vos règles bloquent, ou attendez la fin d'une plage autorisée. TVBalance affiche un message
  sur la télé et la renvoie à l'écran d'accueil ou l'éteint, selon le jeu de règles.
- Essayez **Pause** sur la carte de la télé : l'application des règles s'arrête 30 minutes.
- Essayez **Bonus** pour ajouter 15 ou 30 minutes au budget du jour.

## 5. Connecter Home Assistant
Avec le module complémentaire, confirmez la notification **TVBalance** sous **Paramètres → Appareils et services**.
Chaque télé devient un appareil avec des capteurs, un bouton de pause et des événements pour les automatisations. Voir
[Home Assistant](home-assistant.md).

## 6. L'utiliser depuis le téléphone
Pour recevoir des notifications sur le téléphone et avoir une icône comme une application, ouvrez l'adresse sécurisée et
faites confiance au certificat une fois. Voir [HTTPS sur votre réseau](https.md).

## Et ensuite
- [L'application web](web-ui.md) : règles, tableau de bord, activité et réglages en détail.
- [TVBalance Pro](pro.md) : profils, calendrier, budgets avancés et rapports.
- [Dépannage](troubleshooting.md) si la télé n'est pas trouvée ou si la connexion se coupe.
