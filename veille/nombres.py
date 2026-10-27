"""Lecture des compteurs affichés par les plateformes (« 12,3 k », « 1.2M », « 1 234 »)."""

import re

_SUFFIXES = {"k": 1_000, "m": 1_000_000, "md": 1_000_000_000, "b": 1_000_000_000,
             "mil": 1_000, "mio": 1_000_000}

_MOTIF = re.compile(
    r"^\s*(\d[\d\s  .,]*?)\s*(k|md|mil|mio|m|b)?\s*$", re.IGNORECASE)


def lire_compteur(texte: str | None) -> int | None:
    """Convertit un compteur affiché en entier ; None si le texte n'en est pas un.

    Avec un suffixe (k, M…), la virgule ou le point est décimal : « 12,3 k » = 12 300.
    Sans suffixe, ce sont des séparateurs de milliers : « 1 234 », « 1.234 » = 1 234.
    """
    if not texte:
        return None
    m = _MOTIF.match(texte.replace(" ", " "))
    if not m:
        return None
    chiffres, suffixe = m.group(1), (m.group(2) or "").lower()
    if suffixe:
        chiffres = re.sub(r"[\s  ]", "", chiffres).replace(",", ".")
        if chiffres.count(".") > 1:
            return None
        return int(round(float(chiffres) * _SUFFIXES[suffixe]))
    chiffres = re.sub(r"[\s  .,]", "", chiffres)
    return int(chiffres) if chiffres else None
