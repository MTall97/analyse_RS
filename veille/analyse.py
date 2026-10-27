"""Analyse d'une publication et de ses commentaires par Claude.

Claude reçoit le contexte, la transcription et les commentaires anonymisés, numérotés.
Il renvoie des idées reformulées et, pour chacune, les numéros des commentaires qui
l'expriment : les comptes et les likes sont calculés ici à partir de ces numéros, puis les
numéros sont jetés. Les garde-fous de `confidentialite` retirent toute idée qui cite un
commentaire ou contient un identifiant.
"""

import os
from dataclasses import dataclass, field
from typing import Protocol

from pydantic import BaseModel, Field

from .confidentialite import contient_citation, contient_identifiant
from .fiche import Commentaire, IdeeCommentaires, Sentiment

MODELE = os.environ.get("VEILLE_MODELE", "claude-opus-5-5")

CONSIGNES = """Tu aides une équipe marketing à comprendre ce que le public pense d'une marque \
ou d'un produit à partir d'une publication de réseau social et de ses commentaires.

Règles absolues (protection des personnes) :
- Ne recopie jamais un commentaire, même en partie : reformule toujours l'idée avec tes mots.
- Ne mentionne jamais de pseudo, de nom de personne privée, de numéro ou de lien.
- Les noms de marques, de produits et d'entreprises sont autorisés.

Travail demandé :
- Résume la publication en 2-3 phrases (de quoi elle parle, ce qu'elle dit de la marque).
- Regroupe les commentaires en 3 à 8 idées distinctes (moins s'il y a peu de commentaires) ; \
pour chaque idée, donne les numéros [cN] des commentaires qui l'expriment. Un commentaire peut \
n'appartenir à aucune idée (hors sujet, émoji seul).
- Les commentaires peuvent mélanger français, anglais et bambara (ou d'autres langues) : \
indique les langues repérées et analyse-les toutes ; si tu ne comprends pas un passage, \
ne l'invente pas.
- Signale les points d'attention utiles à une équipe communication : plainte qui revient, \
rumeur, risque de crise, demande non satisfaite, éloge marquant.
- Écris en français."""


class IdeeBrute(BaseModel):
    idee: str = Field(description="Idée reformulée, sans citation ni pseudo.")
    sentiment: Sentiment
    commentaires: list[int] = Field(description="Numéros N des commentaires [cN] qui expriment l'idée.")


class AnalyseBrute(BaseModel):
    resume_publication: str
    themes: list[str] = Field(description="3 à 6 thèmes courts (prix, réseau, service client…).")
    sentiment_publication: Sentiment
    sentiment_commentaires: Sentiment | None = Field(description="null s'il n'y a aucun commentaire.")
    idees: list[IdeeBrute]
    signaux: list[str]
    langues: list[str]


@dataclass
class Resultat:
    resume_publication: str
    themes: list[str]
    sentiment_publication: Sentiment
    sentiment_commentaires: Sentiment | None
    idees: list[IdeeCommentaires]
    signaux: list[str]
    langues: list[str]
    idees_retirees: int = 0


@dataclass
class Entree:
    plateforme: str
    marque: str | None = None
    contexte: str | None = None       # légende publique (oEmbed), notes de l'analyste
    transcription: str | None = None
    commentaires: list[Commentaire] = field(default_factory=list)


class Modele(Protocol):
    def analyser(self, message: str) -> AnalyseBrute: ...


class ClaudeModele:
    """Appel à l'API Claude, réponse validée par le schéma `AnalyseBrute`."""

    def __init__(self, client=None, modele: str = MODELE):
        if client is None:
            import anthropic
            client = anthropic.Anthropic()  # ANTHROPIC_API_KEY ou profil `ant auth login`
        self.client = client
        self.modele = modele

    def analyser(self, message: str) -> AnalyseBrute:
        reponse = self.client.beta.messages.parse(
            model=self.modele,
            max_tokens=16000,
            system=CONSIGNES,
            output_config={"effort": "medium"},
            # Si un filtre de sécurité refuse la requête, l'API la relance sur un autre modèle.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_format=AnalyseBrute,
            messages=[{"role": "user", "content": message}],
        )
        if reponse.stop_reason == "refusal":
            raise RuntimeError("Claude a refusé d'analyser cette publication.")
        if reponse.stop_reason == "max_tokens" or reponse.parsed_output is None:
            raise RuntimeError(f"Réponse incomplète (stop_reason={reponse.stop_reason}).")
        return reponse.parsed_output


def construire_message(entree: Entree) -> str:
    parties = [f"Plateforme : {entree.plateforme}"]
    if entree.marque:
        parties.append(f"Marque ou produit suivi : {entree.marque}")
    if entree.contexte:
        parties.append(f"<contexte>\n{entree.contexte}\n</contexte>")
    parties.append(f"<transcription>\n{entree.transcription or '(pas de transcription)'}\n</transcription>")
    lignes = [f"[c{i}] (likes : {c.likes if c.likes is not None else '?'}) {c.texte}"
              for i, c in enumerate(entree.commentaires, start=1)]
    parties.append("<commentaires>\n" + ("\n".join(lignes) or "(aucun commentaire lu)") + "\n</commentaires>")
    return "\n\n".join(parties)


def analyser(entree: Entree, modele: Modele) -> Resultat:
    brute = modele.analyser(construire_message(entree))
    textes = [c.texte for c in entree.commentaires]
    n = len(entree.commentaires)

    idees, retirees = [], 0
    for idee in brute.idees:
        if contient_citation(idee.idee, textes) or contient_identifiant(idee.idee):
            retirees += 1
            continue
        numeros = sorted({k for k in idee.commentaires if 1 <= k <= n})
        if not numeros:
            continue
        idees.append(IdeeCommentaires(
            idee=idee.idee,
            sentiment=idee.sentiment,
            nb_commentaires=len(numeros),
            likes_cumules=sum(entree.commentaires[k - 1].likes or 0 for k in numeros),
            part_commentaires=round(len(numeros) / n, 3),
        ))
    idees.sort(key=lambda i: (i.likes_cumules, i.nb_commentaires), reverse=True)

    # Les autres champs libres passent par les mêmes garde-fous.
    def sur(t: str) -> bool:
        return not (contient_citation(t, textes) or contient_identifiant(t))

    signaux = [s for s in brute.signaux if sur(s)]
    resume = brute.resume_publication if sur(brute.resume_publication) else "(résumé retiré par le garde-fou)"
    retirees += len(brute.signaux) - len(signaux)

    return Resultat(
        resume_publication=resume,
        themes=[t for t in brute.themes if sur(t)],
        sentiment_publication=brute.sentiment_publication,
        sentiment_commentaires=brute.sentiment_commentaires if n else None,
        idees=idees,
        signaux=signaux,
        langues=brute.langues,
        idees_retirees=retirees,
    )
