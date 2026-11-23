# Téléviseurs LG webOS

TVBalance parle aux téléviseurs LG (webOS 4 et plus récent) par votre réseau domestique. Rien ne sort de chez vous.

## Préparer la télé
1. Connectez la télé au même réseau que l'ordinateur où tourne TVBalance.
2. Activez **Paramètres > Général > Appareils externes > Allumer la TV avec un mobile > Allumer via Wi-Fi** (appelé *LG
   Connect Apps* sur les modèles plus anciens). La télé accepte alors les connexions d'autres appareils.
3. Donnez à la télé une adresse fixe dans votre routeur (une réservation DHCP) pour qu'elle reste joignable.

## Associer
1. Allumez la télé, gardez la télécommande à portée de main et ouvrez **Ajouter une télé** dans l'application web.
2. Choisissez votre télé dans la liste. Si elle n'y est pas (certains réseaux bloquent la recherche), choisissez **LG
   webOS** sous *Saisir l'adresse* et tapez l'adresse IP de la télé, que vous trouvez dans ses réglages réseau.
3. Appuyez sur **Démarrer l'association** et regardez la télé : elle demande si le nouvel appareil doit être autorisé.
   Confirmez avec la télécommande dans les trois minutes. TVBalance conserve la clé fournie par la télé ; vous ne le
   faites qu'une fois par télé.
4. Nommez la télé et choisissez son jeu de règles.

Si vous appuyez sur **Non** ou que rien ne se passe, utilisez **Réessayer**. Si la télé oublie la clé (par exemple après
une réinitialisation d'usine), le tableau de bord affiche **À réassocier** : ouvrez **Associer de nouveau** sur sa
carte et acceptez encore une fois.

## Ce que TVBalance sait faire sur une LG
Lire ce qui est en cours (application, entrée HDMI, chaîne en direct et émission), lister les applications, entrées et
chaînes, afficher un message à l'écran, revenir à l'accueil, ouvrir une application, une entrée ou une chaîne, et
éteindre la télé.

## Limites connues
- **Quick Start+** : avec cette option, la télé répond même écran éteint. TVBalance la signale en veille, pas en train
  d'être regardée, donc le budget quotidien ne s'écoule pas.
- **Les titres des émissions** ne sont disponibles que lorsque la télé en direct est au premier plan, et pas du tout sur
  webOS 4.5 et plus ancien.
- **Allumer la télé** n'est pas encore pris en charge.
- Les icônes des applications sont servies par la télé avec un certificat auto-signé ; l'application web les affiche par
  un proxy dédié.
