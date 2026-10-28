# Veille des avis

Outil pour les équipes marketing et communication : ce que le public pense d'une marque, de
ses produits et de ses concurrents, à partir des publications des réseaux sociaux et de leurs
commentaires.

Pour chaque publication, l'outil produit une **fiche** :
- résumé de la publication, thèmes, sentiment ;
- idées exprimées dans les commentaires, **reformulées**, avec le nombre de commentaires et
  les likes cumulés de chacune ;
- points d'attention (plainte récurrente, rumeur, crise naissante) ;
- statistiques de la vidéo (vues, likes, commentaires, partages, enregistrements) ;
- le lien.

**Aucun pseudo, aucun nom, aucun texte de commentaire n'est enregistré.** Voir
[docs/CONFORMITE.md](docs/CONFORMITE.md).

## Deux modes

### 1. Copilote de l'analyste (`python -m veille.copilote`)
L'analyste navigue lui-même : TikTok sur le PC, ou son téléphone recopié à l'écran (scrcpy,
Lien avec Windows…). Une petite fenêtre reste au premier plan :

1. **Zone des commentaires** : tracer une fois le rectangle où s'affichent les commentaires ;
2. coller le **lien** de la publication, saisir les statistiques affichées ;
3. **Écouter la vidéo** : le son du PC est enregistré, puis transcrit en local ;
4. ouvrir les commentaires, **Lire l'écran**, faire défiler, relire (les doublons sont fusionnés) ;
5. **Terminer la fiche** : analyse, enregistrement, et la mémoire est vidée.

### 2. Vidéo envoyée par le client (`python -m veille.client`)
Le client transmet ce qu'il a le droit de transmettre :

```
python -m veille.client --lien "https://www.tiktok.com/@marque/video/123" --marque "Marque" ^
    --video sa_video.mp4 --captures captures\ --commentaires export.csv ^
    --stats "vues=12k;likes=1,2k;commentaires=340;partages=85"
```

Tout est facultatif sauf le lien. L'export CSV doit avoir une colonne de texte (`texte`, `text`,
`comment`…) et peut avoir une colonne `likes` ; les autres colonnes (auteur…) sont ignorées.

### Synthèse (`python -m veille.rapport --marque "Marque"`)
Rapport Markdown et tableur CSV (une ligne par idée) dans `donnees/rapports/`.

## Installation (Windows)

1. Python 3.11 ou plus récent.
2. `pip install -r requirements.txt` (analyse, mode client sans vidéo) ;
   `pip install -r requirements-local.txt` (copilote, OCR, transcription).
3. [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) avec le français, dans
   `C:\Program Files\Tesseract-OCR\` (le copilote le trouve seul à cet endroit).
4. Clé de l'API Claude : variable d'environnement `ANTHROPIC_API_KEY`.

Réglages par variables d'environnement : `VEILLE_MODELE` (défaut `claude-opus-5-5`),
`VEILLE_LANGUE` (langue de la transcription, défaut `fr`, `auto` pour la détecter).

## Tests

```
python -m pytest
```

## Limites connues
Voir [docs/LIMITES.md](docs/LIMITES.md) : ce qui a été vérifié, ce qui ne l'a pas été.
