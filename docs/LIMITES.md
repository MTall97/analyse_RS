# Limites connues et vérifications faites (27/10/2026)

## Vérifié
- 14 tests (`python -m pytest`) : compteurs, anonymisation, garde-fous, lecture des captures,
  fusion des doublons, parcours copilote et client, contenu du fichier enregistré.
- **OCR sur captures simulées** (pas de vraies captures TikTok), mode clair et sombre, avec
  Tesseract 5 : 3 commentaires sur 3 relus avec leurs likes, sans pseudo. Ce test a révélé un
  défaut, corrigé depuis : l'en-tête « 1 245 commentaires » n'était pas reconnu, et le pseudo
  passait dans le texte.
- **Transcription** (faster-whisper « small », CPU) d'une vidéo à voix de synthèse : phrase
  juste, à un mot près. Avec le modèle « base » et la langue en détection automatique, la
  langue a été prise pour du thaï, d'où la langue imposée par défaut (`VEILLE_LANGUE`).

## Pas encore vérifié
- **L'appel réel à Claude** : aucune clé n'était disponible dans l'environnement de
  développement. La requête est testée avec un client factice (paramètres, refus), pas la
  qualité des idées produites.
- **La fenêtre du copilote** (Tkinter), la capture d'écran (mss) et l'écoute du son du PC
  (soundcard, boucle WASAPI) : écrites pour Windows, à essayer sur la machine de l'analyste.
- **La lecture de vraies captures TikTok** : la mise en page réelle (application, site,
  langue de l'interface, badges « Créateur », réponses imbriquées) peut casser l'heuristique de
  `ocr_tiktok.py`. Il faut la recaler sur 10 à 20 vraies captures, gardées hors du dépôt.

## Limites de fond
- **Pseudos sous forme de nom affiché** (« Aminata Traoré », avec espace) : si une ligne
  d'interface non reconnue décale un bloc, un tel nom peut passer dans le texte envoyé à
  l'analyse. La consigne donnée à Claude et le garde-fou de sortie l'empêchent d'arriver dans
  la fiche, mais il est transmis à l'API.
- **Bambara** : Whisper ne le transcrit pas, et Tesseract le lit comme du français. Claude
  comprend une partie du bambara écrit, sans garantie. Un modèle bambara (projet
  `transduction_Bam_Englais`) pourra remplacer `sources.transcrire`.
- **Statistiques de la vidéo** : saisies à la main par l'analyste, pas lues à l'écran.
- **Échantillon** : ce sont les commentaires *lus* qui comptent, pas tous les commentaires.
  `part_commentaires` est une part de l'échantillon lu, à ne pas présenter comme un sondage.
- **Dépendances** : faster-whisper 1.2.1 ne marche pas avec PyAV 19 (erreur `metadata_errors`) ;
  `requirements-local.txt` fixe `av<16`.
