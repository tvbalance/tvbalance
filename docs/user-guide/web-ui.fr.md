# L'application web

L'application web de TVBalance fonctionne dans n'importe quel navigateur de votre réseau domestique, et dans Home
Assistant comme panneau latéral. Elle est confortable sur téléphone et peut être ajoutée à l'écran d'accueil comme une
application. Elle parle anglais, italien, allemand, français et espagnol.

## Premier lancement
À la première visite, l'application demande trois choses :
1. **Un mot de passe** pour l'administrateur (10 caractères au minimum). Gardez-le en lieu sûr ; il ouvre tout.
2. **La langue et le fuseau horaire.** Les horaires et les limites quotidiennes suivent ce fuseau.
3. **Un premier jeu de règles**, à partir de « Jours d'école » (en semaine 16 h–20 h, le week-end 9 h–21 h, deux heures
   par jour, avertissements à 10 et 5 minutes) ou d'un jeu vide. Tout peut être modifié ensuite.

## Ajouter une télé
Tant qu'il n'y a aucune télé, le tableau de bord propose **Ajouter une télé** (réservé aux administrateurs ; une
session PIN ne le voit jamais). L'assistant explore votre réseau ou accepte l'adresse de la télé saisie à la main, vous
guide pour accepter la connexion sur la télé et se termine par le nom de la télé et le choix de son jeu de règles. Une
télé qui a perdu sa clé affiche **À réassocier** avec un lien **Associer de nouveau**. Les étapes propres à chaque
marque sont dans les guides des télés, par exemple [LG webOS](tv-lg-webos.md).

## Se connecter
- **Mot de passe :** accès complet.
- **PIN :** un code court facultatif pour un appareil partagé, comme une tablette dans la cuisine. Une session PIN peut
  consulter le tableau de bord et utiliser les commandes parentales, mais ne peut modifier ni les règles, ni les mots
  de passe, ni les jetons. Après cinq PIN erronés, elle se verrouille un moment.
- Dans Home Assistant, vous êtes déjà connecté par Home Assistant.

## Tableau de bord
Une carte par télé indique si elle est allumée, ce qui est en cours, combien de minutes ont été regardées et combien il
en reste, et si le contenu actuel est autorisé. La carte se met à jour toute seule.

Commandes parentales sur chaque carte :
- **Pause** suspend l'application des règles pendant 30 minutes.
- **Bonus** ajoute 15 ou 30 minutes au budget du jour.
- **Autoriser** ou **Bloquer** prend le dessus sur les règles pendant 15, 30, 60 ou 120 minutes, ou jusqu'à minuit.
- **Annuler le forçage** revient aux règles.

## Règles
Un jeu de règles définit quand et combien de temps une télé peut être utilisée. Plusieurs télés peuvent partager un même
jeu, et chaque télé en suit un. Ouvrez **Règles**, choisissez un jeu (ou créez-en un) et modifiez-le dans quatre
onglets :

- **Horaires :** les plages de chaque jour de la semaine. Ajoutez autant de plages que nécessaire, copiez un jour sur
  d'autres et ajoutez des jours spéciaux pour une date précise, comme un jour férié. Une plage qui se termine avant son
  début passe minuit.
- **Durée :** un budget quotidien facultatif en minutes et les avertissements qui apparaissent quand il reste ce nombre
  de minutes. Avec Pro, vous pouvez aussi fixer un budget pour chaque jour de la semaine, des quotas partagés pour des
  groupes d'applications et reporter le temps non utilisé au lendemain. Voir [TVBalance Pro](pro.md).
- **Contenus :** les applications, entrées et chaînes à bloquer ; un mode « Autoriser seulement les applications
  choisies » ; ce qui est toujours autorisé ; et où la télé va quand quelque chose est bloqué (accueil, une application,
  une entrée ou une chaîne). Choisissez les éléments dans la liste lue sur la télé, avec les icônes des applications. Si
  la télé est éteinte ou injoignable, saisissez les identifiants à la main.
- **Avancé :** la rigueur avec laquelle les blocages sont appliqués. Les valeurs par défaut conviennent presque à tous.

### Profils et calendrier (Pro)
*Activer comme profil* sur un jeu de règles l'applique à toutes les télés du foyer pour la durée choisie, sauf celles
que vous cochez. Le tableau de bord montre le profil actif et vous laisse l'arrêter ; chaque carte de télé affiche son
nom. **Règles > Calendrier** liste les entrées qui activent des jeux de règles automatiquement, chaque semaine ou entre
deux dates. Voir [TVBalance Pro](pro.md).

Si un jeu de règles ne peut pas être enregistré, un message nomme le problème, par exemple une destination de repli
elle-même bloquée, un avertissement plus long que le budget ou deux plages qui se chevauchent.

## Détails de la télé et activité
Dans le tableau de bord, choisissez le nom d'une télé pour la renommer, activer ou désactiver la surveillance, changer
son jeu de règles, voir les sept derniers jours en barres et lire ses derniers événements. Retirer une télé demande une
confirmation.

**Activité** montre la même chose pour toutes les télés, avec un filtre et le journal complet des événements :
avertissements, blocages, extinctions et problèmes de connexion. Avec Pro, vous choisissez une période plus longue
(jusqu'à un an), voyez les applications les plus regardées et lisez le rapport de la semaine passée. Voir
[TVBalance Pro](pro.md).

Modifier les règles, les télés et les réglages demande le mot de passe administrateur.

Si vous ouvrez l'application web par une simple adresse `http://` alors que le moteur propose HTTPS, un bandeau suggère
l'adresse sécurisée. Vous pouvez le fermer ; le choix est mémorisé dans ce navigateur.

## Réglages
- **Général :** langue, fuseau horaire et thème clair ou sombre.
- **Notifications :** vous recevez sur cet appareil une notification push quand la télé doit être associée de nouveau,
  est injoignable, qu'un contenu a été bloqué ou que le temps va se terminer. Choisissez celles que vous voulez,
  envoyez un test, désactivez-les et retirez d'autres appareils. Seul l'administrateur voit cette carte. Les
  navigateurs n'autorisent le push que sur une connexion sécurisée : cela fonctionne donc via Home Assistant en HTTPS
  (Ingress), depuis `localhost` ou depuis l'adresse sécurisée de votre réseau (voir https.md), pas depuis une simple
  adresse `http://`. La carte renvoie vers l'adresse sécurisée quand elle existe. Sur iPhone et iPad, ajoutez d'abord
  TVBalance à l'écran d'accueil.
- **TVBalance Pro :** l'offre actuelle, à qui la licence est destinée et quand elle expire, un champ pour coller une clé
  de licence et un bouton pour la retirer. Seul l'administrateur voit cette carte. Voir pro.md.
- **Connexion sécurisée :** les adresses HTTPS, l'expiration et l'empreinte du certificat, les téléchargements du
  certificat et du profil pour iPhone et iPad, les étapes d'installation par appareil et un bouton pour créer un
  nouveau certificat. Seul l'administrateur voit cette carte. Voir https.md.
- **Sécurité :** changer le mot de passe ; définir ou retirer le PIN parental.
- **Appareils connectés :** voir chaque navigateur connecté et en déconnecter un ou tous sauf celui-ci.
- **Jetons d'API :** pour d'autres programmes. Le secret d'un jeton n'est affiché qu'une fois à la création : copiez-le
  tout de suite. Choisissez **lecture** et **contrôle** pour Home Assistant (voir home-assistant.md). Un jeton peut être
  révoqué à tout moment.

**Système** indique la version et les marques de télé prises en charge par cette version, avec leur niveau de maturité.
