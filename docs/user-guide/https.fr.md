# HTTPS sur votre réseau

TVBalance peut répondre en HTTPS sur votre réseau domestique. Les navigateurs traitent alors l'application web comme
sécurisée : les notifications Web Push fonctionnent, le cookie de connexion est marqué `Secure` et votre mot de passe
n'est plus envoyé en clair.

HTTPS est activé par défaut. Le moteur écoute sur deux ports :

| Port | Protocole | Utilisé pour |
| ---- | --------- | ------------ |
| 8765 | HTTP      | L'Ingress de Home Assistant, le contrôle de santé, la découverte du module et un premier coup d'œil depuis un navigateur |
| 8766 | HTTPS     | L'application web et l'API sur votre réseau |

HTTP reste ouvert volontairement. Quand vous ouvrez l'application web en `http://`, un bandeau propose l'adresse
sécurisée, et la carte Notifications y renvoie.

## Le certificat

Une adresse web sur votre propre réseau (`tvbalance.local`, `10.x.x.x`) ne peut pas obtenir de certificat d'une autorité
publique. TVBalance crée donc une petite **autorité de certification locale** (AC) au premier démarrage et signe avec
elle son propre certificat de serveur. Le certificat de serveur dure 397 jours et se renouvelle tout seul 30 jours avant
son expiration, sans redémarrage. Il change aussi quand le nom ou l'adresse du moteur change.

Vos appareils doivent faire confiance à l'AC une fois. D'ici là, un navigateur avertit que la connexion n'est pas
privée.

### Installer l'AC sur un appareil

Ouvrez **Réglages → Connexion sécurisée** dans l'application web. Elle liste les adresses sécurisées, l'expiration du
certificat et son **empreinte**, et propose deux téléchargements : le certificat (`.crt`) et un profil pour iPhone et
iPad.

Comparez l'empreinte affichée par l'appareil à celle des Réglages avant de faire confiance.

- **iPhone et iPad :** ouvrez le profil, autorisez-le dans Réglages, installez-le, puis activez-le dans Réglages →
  Général → Informations → Réglages de confiance des certificats.
- **Android :** Paramètres → cherchez « certificat d'AC » → Installer quand même → choisissez le fichier téléchargé.
- **Windows :** ouvrez le fichier → Installer le certificat → Ordinateur local → Autorités de certification racines de
  confiance.
- **macOS :** ouvrez le fichier dans Trousseau d'accès, puis réglez la confiance sur Toujours approuver.

Sous Windows et Linux, certains navigateurs ont leur propre liste d'autorités (Firefox en a une) : importez aussi le
fichier là.

### Repartir de zéro avec une nouvelle AC

**Créer un nouveau certificat** sur la même carte crée une nouvelle AC et un nouveau certificat de serveur. Utilisez-le
si un appareil qui faisait confiance à l'ancienne AC est perdu ou si vous soupçonnez que la clé de l'AC a fuité. Chaque
appareil doit alors installer la nouvelle AC, et l'intégration Home Assistant vous demande de confirmer la nouvelle
empreinte.

## Votre propre certificat

Si vous avez déjà un certificat auquel vos appareils font confiance (par exemple celui de Home Assistant), indiquez-le à
TVBalance à la place :

- Moteur autonome : définissez `TVBALANCE_TLS_CERTFILE` et `TVBALANCE_TLS_KEYFILE` sur la chaîne de certificats et la clé
  privée, deux fichiers PEM.
- Module complémentaire Home Assistant : placez les fichiers dans le dossier `/ssl` et renseignez **Fichier de
  certificat** et **Fichier de clé** dans les options du module (par exemple `fullchain.pem` et `privkey.pem`).

Le moteur vérifie que la clé correspond au certificat et qu'il n'a pas expiré. Réglages → Connexion sécurisée n'affiche
alors que l'état, car le renouvellement vous revient. Redémarrez le moteur après avoir remplacé les fichiers.

## Réglages

| Variable d'environnement | Option du module | Signification |
| ------------------------ | ---------------- | ------------- |
| `TVBALANCE_TLS` | HTTPS | `auto` (défaut) ou `off` |
| `TVBALANCE_HTTPS_PORT` | | Port HTTPS, 8766 par défaut (doit différer de `TVBALANCE_PORT`) |
| `TVBALANCE_TLS_CERTFILE`, `TVBALANCE_TLS_KEYFILE` | Fichier de certificat, Fichier de clé | Votre propre certificat |
| `TVBALANCE_TLS_NAMES` | Noms supplémentaires | Autres noms d'hôte ou adresses pour le certificat automatique, séparés par des virgules |

Les variables d'environnement l'emportent sur les options du module.

Le certificat automatique couvre `localhost`, le nom d'hôte de la machine et son nom `.local`, ainsi que son adresse
IPv4 privée. Les noms non locaux sont écartés, et les Réglages vous disent lesquels.

Si le port HTTPS est occupé, le moteur journalise une erreur et continue de servir en HTTP.

## Home Assistant

En HTTP à l'intérieur du module, rien ne change. Pour connecter l'intégration en HTTPS, saisissez une adresse
`https://` et le jeton d'API. Quand le certificat du moteur n'est pas approuvé, l'intégration télécharge l'AC, affiche
son empreinte et vous demande de la comparer à Réglages → Connexion sécurisée. Après votre confirmation, Home Assistant
n'accepte que cette AC pour ce moteur. Si l'AC change plus tard, une réauthentification demande de confirmer à nouveau.

## Notes de sécurité

- **Ce que l'AC peut signer.** L'AC porte des contraintes de noms X.509 : elle ne peut émettre que des certificats pour
  `localhost`, `.local`, `.lan`, `.home.arpa`, `.internal` et les plages d'adresses privées. Un appareil qui lui fait
  confiance n'est pas exposé à un faux certificat pour un site public, tant que le client applique les contraintes de
  noms (les navigateurs et systèmes actuels le font).
- **Où se trouve la clé.** La clé de l'AC est stockée scellée avec les autres secrets du moteur (`secret.key`), et la
  clé du serveur est un fichier aux droits réservés au propriétaire dans le dossier de données. Quiconque peut lire le
  dossier de données peut émettre des certificats pour des noms locaux ; protégez-le comme le reste de vos sauvegardes.
- **Le téléchargement est public.** Le certificat de l'AC (jamais sa clé) peut être téléchargé sans connexion, car un
  nouvel appareil en a besoin avant de pouvoir faire confiance à quoi que ce soit. Confirmez toujours l'empreinte : c'est
  la vérification que le fichier vient de votre moteur.
- **HTTP reste disponible.** Connectez-vous en HTTPS sur les réseaux partagés. Le bandeau est là pour vous le rappeler.
