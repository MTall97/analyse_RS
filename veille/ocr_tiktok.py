"""Reconstitution des commentaires à partir du texte lu (OCR) sur une capture d'écran.

Sur TikTok (application et site), un commentaire s'affiche ainsi :

    pseudo                          <- toujours jeté
    texte du commentaire (1 ligne ou plus)
    3j  Répondre             ♡ 45   <- ligne « méta » : date, Répondre, parfois les likes
    Voir 4 réponses                 <- bruit d'interface

La ligne méta ferme un bloc : la première ligne du bloc est le pseudo, on la retire ; le
reste est le texte. Les likes sont le nombre seul au bout de la ligne méta ou sur sa
propre ligne. Un bloc d'une seule ligne est ignoré, faute de pouvoir séparer le pseudo du
texte. Heuristique à recaler sur de vraies captures (voir docs/LIMITES.md).
"""

import re

from .confidentialite import anonymiser
from .fiche import Commentaire
from .nombres import lire_compteur

_REPONDRE = r"(répondre|repondre|reply|responder|antwort)"
_DUREE = r"\d+\s*(s|sec|min|mn|h|j|d|sem|w|mois|mo|an|ans|y)"
_DATE = r"(\d{1,4}[-/]\d{1,2}([-/]\d{1,4})?)"
_FIN_META = r"[\s♡♥❤️\d.,kKmM]*$"  # après la date et « Répondre », seulement les likes
# Lignes courtes seulement : « il y a 5 ans que j'utilise… » est un commentaire, pas une date.
_META = re.compile(
    rf"^(il y a\s+)?({_DUREE}|{_DATE}|hier|yesterday|à l'instant|just now)(\s+ago)?"
    rf"(\s*[·•]?\s*{_REPONDRE})?{_FIN_META}"
    rf"|^.{{0,25}}\b{_REPONDRE}\b{_FIN_META}",
    re.IGNORECASE)
_LIKES_EN_FIN = re.compile(r"[♡♥❤️\s]*(\d[\d\s.,]*\s*[kKmM]?)\s*$")
# Un seul mot avec chiffre, point ou tiret bas : un pseudo, pas un commentaire.
_PSEUDO = re.compile(r"^@?[\w.]*[\d_.][\w.]*$")
_NOMBRE_SEUL = re.compile(r"^[♡♥❤️\s]*\d[\d\s.,]*\s*[kKmM]?\s*$")
_BRUIT = re.compile(
    r"^(voir|afficher|view|ver|masquer|hide)\b.*(réponse|reponse|repl|respuesta|plus|more)"
    r"|^[\d\s.,]+[kKmM]?\s+(commentaires?|comments?)$"
    r"|^(commentaires?|comments?)$"
    r"|^(ajouter un commentaire|add comment|écrire un commentaire)"
    r"|^(auteur|créateur|creator|author|épinglé|pinned)$",
    re.IGNORECASE)


def _likes_meta(ligne: str) -> int | None:
    m = _LIKES_EN_FIN.search(ligne)
    if not m:
        return None
    # « 3j Répondre » : le nombre de la durée n'est pas un compteur de likes.
    avant = ligne[:m.start()].strip()
    if not avant or not re.search(_REPONDRE, avant, re.IGNORECASE):
        return None
    return lire_compteur(m.group(1))


def lire_commentaires(lignes: list[str]) -> tuple[list[Commentaire], int]:
    """Renvoie les commentaires lus (sans pseudo) et le nombre de blocs ignorés."""
    commentaires: list[Commentaire] = []
    ignores = 0
    bloc: list[str] = []
    likes_bloc: int | None = None
    dernier: Commentaire | None = None

    for brute in lignes:
        ligne = brute.strip()
        if not ligne or _BRUIT.search(ligne):
            continue
        if _NOMBRE_SEUL.match(ligne):
            n = lire_compteur(ligne.strip("♡♥❤️ "))
            if bloc:
                likes_bloc = n
            elif dernier is not None and dernier.likes is None:
                dernier.likes = n
            continue
        if _META.match(ligne):
            # La première ligne est le pseudo ; si une ligne d'interface non reconnue l'a
            # précédé, le pseudo est la ligne suivante : on retire aussi ce qui y ressemble.
            corps = bloc[1:]
            while corps and _PSEUDO.match(corps[0]):
                corps = corps[1:]
            if corps:
                texte = anonymiser(" ".join(corps))
                likes = _likes_meta(ligne)
                dernier = Commentaire(texte, likes if likes is not None else likes_bloc)
                commentaires.append(dernier)
            elif bloc:
                ignores += 1
            bloc, likes_bloc = [], None
            continue
        bloc.append(ligne)

    if bloc:
        ignores += 1  # bloc coupé en bas de l'écran : il sera relu au défilement suivant
    return commentaires, ignores


def fusionner(existants: list[Commentaire], nouveaux: list[Commentaire]) -> list[Commentaire]:
    """Ajoute les commentaires d'une nouvelle capture sans doublon (défilement qui se chevauche)."""
    index = {_cle(c.texte): c for c in existants}
    for c in nouveaux:
        cle = _cle(c.texte)
        if cle in index:
            if c.likes is not None and (index[cle].likes or 0) < c.likes:
                index[cle].likes = c.likes
        else:
            index[cle] = c
            existants.append(c)
    return existants


def _cle(texte: str) -> str:
    return re.sub(r"\W+", "", texte.lower())
