"""Module 2 : analyser une vidéo envoyée par le client.

Le client fournit le lien et ce qu'il a le droit de transmettre : le fichier vidéo (sa
propre vidéo, ou une vidéo dont il a les droits), des captures d'écran des commentaires,
un export CSV des commentaires de son compte, les statistiques affichées.

    python -m veille.client --lien URL --marque "Orange Mali" \\
        --video ma_video.mp4 --captures captures/ --commentaires export.csv \\
        --stats "vues=12k;likes=1,2k;commentaires=340;partages=85"
"""

import argparse
from pathlib import Path

from .analyse import ClaudeModele, Entree
from .fiche import StatsVideo
from .ocr_tiktok import fusionner, lire_commentaires
from .pipeline import DOSSIER_DONNEES, enregistrer, produire_fiche
from .sources import (infos_publiques, lignes_ocr, lire_export_commentaires, lire_stats,
                      plateforme, transcrire)

IMAGES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


def images(chemins: list[Path]) -> list[Path]:
    trouvees = []
    for chemin in chemins:
        if chemin.is_dir():
            trouvees += sorted(p for p in chemin.iterdir() if p.suffix.lower() in IMAGES)
        else:
            trouvees.append(chemin)
    return trouvees


def preparer_entree(lien: str, marque: str | None = None, video: Path | None = None,
                    captures: list[Path] = (), commentaires: Path | None = None,
                    notes: str | None = None, *, ocr=lignes_ocr, transcrire=transcrire,
                    infos=infos_publiques) -> Entree:
    entree = Entree(plateforme=plateforme(lien), marque=marque)
    contexte = [infos(lien).get("titre"), notes]
    entree.contexte = "\n".join(c for c in contexte if c) or None
    if video:
        entree.transcription, _ = transcrire(str(video))
    lus = []
    for image in images(list(captures)):
        nouveaux, _ = lire_commentaires(ocr(image))
        fusionner(lus, nouveaux)
    if commentaires:
        fusionner(lus, lire_export_commentaires(commentaires))
    entree.commentaires = lus
    return entree


def main(argv=None):
    p = argparse.ArgumentParser(description="Analyser une vidéo envoyée par le client.")
    p.add_argument("--lien", required=True)
    p.add_argument("--marque")
    p.add_argument("--video", type=Path, help="fichier vidéo ou audio à transcrire")
    p.add_argument("--captures", type=Path, nargs="*", default=[],
                   help="images ou dossiers de captures des commentaires")
    p.add_argument("--commentaires", type=Path, help="export CSV (colonne texte, likes facultative)")
    p.add_argument("--stats", help="« vues=12k;likes=1,2k;commentaires=340;partages=85;enregistrements=40 »")
    p.add_argument("--notes", help="contexte donné par le client")
    p.add_argument("--donnees", type=Path, default=DOSSIER_DONNEES)
    a = p.parse_args(argv)

    entree = preparer_entree(a.lien, a.marque, a.video, a.captures, a.commentaires, a.notes)
    stats = StatsVideo(**{k: v for k, v in lire_stats(a.stats).items() if k in StatsVideo.model_fields})
    fiche = produire_fiche(entree, a.lien, "client", ClaudeModele(), stats)
    chemin = enregistrer(fiche, a.donnees)
    print(fiche.model_dump_json(indent=2))
    print(f"\nFiche ajoutée à {chemin}")


if __name__ == "__main__":
    main()
