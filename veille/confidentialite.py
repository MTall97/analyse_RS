"""Protection des personnes : rien d'identifiant ne sort de l'analyse.

Deux garde-fous :
- `anonymiser` retire du texte des commentaires ce qui identifie quelqu'un (@pseudo,
  courriel, téléphone, lien) avant tout envoi à l'analyse ;
- `contient_citation` vérifie qu'une idée produite par l'analyse ne recopie pas un
  commentaire : on garde des idées reformulées, jamais le texte des gens.
"""

import re
import unicodedata

_MENTION = re.compile(r"@[\w.\-]+")
_COURRIEL = re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+")
_LIEN = re.compile(r"(https?://|www\.)\S+", re.IGNORECASE)
# Numéros de téléphone : 8 chiffres ou plus, avec espaces, points, tirets ou indicatif.
_TELEPHONE = re.compile(r"(?<!\w)\+?\d[\d\s.\-]{6,}\d(?!\w)")

TAILLE_CITATION = 6
"""Nombre de mots consécutifs repris d'un commentaire à partir duquel on parle de citation."""


def anonymiser(texte: str) -> str:
    texte = _COURRIEL.sub("[courriel]", texte)
    texte = _LIEN.sub("[lien]", texte)
    texte = _MENTION.sub("[pseudo]", texte)
    texte = _TELEPHONE.sub("[téléphone]", texte)
    return re.sub(r"\s+", " ", texte).strip()


def _mots(texte: str) -> list[str]:
    texte = unicodedata.normalize("NFKD", texte.lower())
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    return re.findall(r"\w+", texte)


def _sequences(mots: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(mots[i:i + n]) for i in range(len(mots) - n + 1)}


def contient_citation(sortie: str, commentaires: list[str], n: int = TAILLE_CITATION) -> bool:
    """Vrai si `sortie` reprend au moins `n` mots consécutifs d'un des commentaires."""
    seq_sortie = _sequences(_mots(sortie), n)
    if not seq_sortie:
        return False
    return any(seq_sortie & _sequences(_mots(c), n) for c in commentaires)


def contient_identifiant(sortie: str) -> bool:
    """Vrai si `sortie` contient un @pseudo, un courriel, un téléphone ou un lien."""
    return any(m.search(sortie) for m in (_MENTION, _COURRIEL, _LIEN, _TELEPHONE))
