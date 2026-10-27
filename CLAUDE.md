# Contexte du projet (pour les agents IA et les nouveaux contributeurs)

## Objet
Veille des avis sur les réseaux sociaux pour les équipes marketing et communication : une fiche
par publication (résumé, idées des commentaires reformulées, chiffres, lien). Marché visé :
d'abord le Mali (français, bambara). L'utilisateur travaille en français.

## Règles
- **Pas d'automatisation de compte** : aucun robot ne pilote un compte, un navigateur connecté ou un
  téléphone émulé, et aucun code de contournement de la détection. Les modes autorisés sont le
  copilote (un humain navigue) et les données fournies par le client ou par les API officielles.
  Voir `docs/CONFORMITE.md`.
- **Rien d'identifiant sur le disque** : captures, son, transcription et texte des commentaires
  restent en mémoire. Seule la `Fiche` (`veille/fiche.py`) est écrite. Ne jamais ajouter de champ
  qui contienne un pseudo, un nom de particulier ou un texte de commentaire.
- Toute sortie de l'analyse passe par les garde-fous de `veille/confidentialite.py`.
- **Dans le dépôt**, aucune vraie capture, aucun vrai commentaire, aucune vraie fiche : seulement des
  exemples inventés (`donnees/` est ignoré par Git).
- Ne pas présenter comme vérifié ce qui ne l'a pas été : tenir `docs/LIMITES.md` à jour.
- Tests : `python -m pytest` avant chaque commit.

## Code
- `veille/ocr_tiktok.py` : commentaires à partir du texte OCR (pseudo jeté).
- `veille/analyse.py` : appel à Claude (sortie structurée), comptes et likes calculés dans le code.
- `veille/sources.py` : oEmbed, transcription (faster-whisper), OCR (Tesseract), export CSV.
- `veille/copilote.py` (module 1, Tkinter, Windows), `veille/client.py` (module 2),
  `veille/rapport.py` (synthèse).
