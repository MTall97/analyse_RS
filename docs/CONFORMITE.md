# Conformité : règles des plateformes et données personnelles

## Ce que l'outil fait, et ce qu'il ne fait pas

| | |
|---|---|
| ✅ Un humain navigue, l'outil l'assiste sur sa propre machine | ❌ Aucun robot ne pilote un compte ou un téléphone émulé |
| ✅ Lecture de ce qui est affiché à l'écran de l'analyste | ❌ Aucune collecte automatique, aucun contournement de détection |
| ✅ Données fournies par le client (ses vidéos, ses exports) | ❌ Aucun téléchargement de vidéo de tiers |
| ✅ Informations publiques par l'oEmbed officiel (TikTok, YouTube) | |

**Pourquoi.** Les conditions d'utilisation de TikTok, Meta, X et LinkedIn interdisent l'accès
par des moyens automatisés, même à un rythme lent. Avec un compte connecté, c'est une
rupture du contrat accepté à l'inscription. Le risque concerne surtout l'entreprise : comptes
bannis, outil cassé par une mise à jour, clients qui demandent d'où viennent les données. Le
mode copilote réduit fortement ce risque, puisque c'est un humain qui accède au contenu, sans
l'annuler. À faire vérifier par un juriste avant de vendre le service.

## Données personnelles (RGPD, loi malienne n° 2013-015, APDP)

Même publics, des commentaires sont des données personnelles. L'outil applique la
**minimisation** :

1. **En mémoire seulement** : captures d'écran, son, transcription, texte des commentaires.
   Tout est effacé à la fin de chaque fiche (`Session.vider`).
2. **Anonymisation avant l'analyse** : la ligne du pseudo est retirée à la lecture de l'écran,
   et les colonnes autres que le texte et les likes sont ignorées dans les exports. Les
   @mentions, courriels, téléphones et liens sont remplacés (`confidentialite.anonymiser`).
3. **Reformulation imposée** : Claude regroupe les commentaires en idées et doit les reformuler.
   Un garde-fou retire toute idée qui reprend six mots consécutifs d'un commentaire ou
   contient un identifiant (`confidentialite.contient_citation`, `contient_identifiant`). Le
   nombre d'idées retirées est noté dans la fiche (`idees_retirees`).
4. **Ce qui est écrit** : la fiche seule (`donnees/fiches.jsonl`), c'est-à-dire des idées,
   des chiffres et le lien.

### Points restants
- **Le lien** d'une vidéo TikTok contient le @pseudo de son auteur. Pour une marque ou un
  créateur public, c'est acceptable. Pour un particulier, il faudrait ne garder que
  l'identifiant numérique de la vidéo : à décider.
- **Envoi à l'API Claude** : le texte anonymisé des commentaires est transmis à Anthropic
  pour l'analyse, qui agit alors comme sous-traitant. À mentionner dans le registre des
  traitements et dans le contrat avec les clients. Vérifier les conditions de conservation
  des données de l'API.
- **Base légale** : intérêt légitime (étude d'opinion agrégée), à documenter. Il faut aussi
  fixer une durée de conservation des fiches.
- **Pas de profilage** : l'outil ne suit pas les personnes et ne relie pas leurs
  commentaires d'une publication à l'autre. Ne pas l'étendre dans ce sens.
