"""De l'entrée à la fiche enregistrée."""

import json
from datetime import datetime, timezone
from pathlib import Path

from .analyse import Entree, Modele, analyser
from .fiche import Fiche, StatsVideo, stats_commentaires

DOSSIER_DONNEES = Path("donnees")


def produire_fiche(entree: Entree, lien: str, source: str, modele: Modele,
                   stats_video: StatsVideo | None = None) -> Fiche:
    resultat = analyser(entree, modele)
    return Fiche(
        lien=lien,
        plateforme=entree.plateforme,
        marque=entree.marque,
        source=source,
        date_analyse=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        resume_publication=resultat.resume_publication,
        themes=resultat.themes,
        sentiment_publication=resultat.sentiment_publication,
        sentiment_commentaires=resultat.sentiment_commentaires,
        idees_commentaires=resultat.idees,
        signaux=resultat.signaux,
        langues=resultat.langues,
        stats_video=stats_video or StatsVideo(),
        stats_commentaires=stats_commentaires(entree.commentaires),
        transcription_disponible=bool(entree.transcription),
        idees_retirees=resultat.idees_retirees,
    )


def enregistrer(fiche: Fiche, dossier: Path = DOSSIER_DONNEES) -> Path:
    """Ajoute la fiche à `fiches.jsonl` : seule trace écrite d'une analyse."""
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / "fiches.jsonl"
    with open(chemin, "a", encoding="utf-8") as f:
        f.write(fiche.model_dump_json() + "\n")
    return chemin


def lire_fiches(dossier: Path = DOSSIER_DONNEES) -> list[Fiche]:
    chemin = dossier / "fiches.jsonl"
    if not chemin.exists():
        return []
    with open(chemin, encoding="utf-8") as f:
        return [Fiche.model_validate(json.loads(l)) for l in f if l.strip()]
