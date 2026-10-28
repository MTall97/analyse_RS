"""Format des données.

`Commentaire` n'existe qu'en mémoire, le temps d'une analyse. Ce qui est enregistré est
la `Fiche` : idées reformulées et chiffres, sans nom ni texte de commentaire.
"""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

Sentiment = Literal["positif", "negatif", "neutre", "mitige"]


@dataclass
class Commentaire:
    """Commentaire lu, en mémoire seulement : jamais écrit sur le disque."""
    texte: str
    likes: int | None = None


class StatsVideo(BaseModel):
    vues: int | None = None
    likes: int | None = None
    commentaires: int | None = None
    partages: int | None = None
    enregistrements: int | None = None


class StatsCommentaires(BaseModel):
    lus: int = 0
    likes_total: int = 0
    likes_median: float | None = None


class IdeeCommentaires(BaseModel):
    idee: str = Field(description="Idée reformulée, jamais citée.")
    sentiment: Sentiment
    nb_commentaires: int
    likes_cumules: int
    part_commentaires: float = Field(description="Part des commentaires lus qui expriment cette idée (0-1).")


class Fiche(BaseModel):
    lien: str
    plateforme: str
    marque: str | None = None
    source: Literal["copilote", "client"]
    date_analyse: str
    resume_publication: str
    themes: list[str]
    sentiment_publication: Sentiment
    sentiment_commentaires: Sentiment | None
    idees_commentaires: list[IdeeCommentaires]
    signaux: list[str] = Field(default_factory=list,
                               description="Points d'attention : plainte récurrente, rumeur, crise naissante…")
    langues: list[str] = Field(default_factory=list)
    stats_video: StatsVideo = Field(default_factory=StatsVideo)
    stats_commentaires: StatsCommentaires = Field(default_factory=StatsCommentaires)
    transcription_disponible: bool = False
    idees_retirees: int = Field(0, description="Idées écartées par le garde-fou (citation ou identifiant).")


def stats_commentaires(commentaires: list[Commentaire]) -> StatsCommentaires:
    likes = sorted(c.likes for c in commentaires if c.likes is not None)
    mediane = None
    if likes:
        milieu = len(likes) // 2
        mediane = float(likes[milieu]) if len(likes) % 2 else (likes[milieu - 1] + likes[milieu]) / 2
    return StatsCommentaires(lus=len(commentaires), likes_total=sum(likes), likes_median=mediane)
