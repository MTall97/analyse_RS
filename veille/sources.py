"""Entrées : informations publiques d'un lien, transcription, OCR, export de commentaires.

Les bibliothèques lourdes (faster-whisper, pytesseract) ne sont importées qu'à l'usage :
le reste du paquet fonctionne et se teste sans elles.
"""

import csv
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

from .confidentialite import anonymiser
from .fiche import Commentaire
from .nombres import lire_compteur

OEMBED = {
    "tiktok": "https://www.tiktok.com/oembed?url={}",
    "youtube": "https://www.youtube.com/oembed?format=json&url={}",
}


def plateforme(lien: str) -> str:
    hote = urllib.parse.urlparse(lien).netloc.lower()
    for nom, motif in (("tiktok", "tiktok."), ("youtube", "youtu"), ("instagram", "instagram."),
                       ("facebook", "facebook."), ("facebook", "fb.watch"), ("x", "x.com"),
                       ("x", "twitter."), ("linkedin", "linkedin.")):
        if motif in hote:
            return nom
    return "autre"


def infos_publiques(lien: str, ouvrir=urllib.request.urlopen) -> dict:
    """Légende publique d'une vidéo par l'oEmbed officiel (TikTok, YouTube) ; {} sinon.

    Seul le titre sert, comme contexte de l'analyse : il n'est pas enregistré.
    """
    modele = OEMBED.get(plateforme(lien))
    if not modele:
        return {}
    requete = urllib.request.Request(modele.format(urllib.parse.quote(lien, safe="")),
                                     headers={"User-Agent": "veille-avis/0.1"})
    try:
        with ouvrir(requete, timeout=15) as r:
            donnees = json.loads(r.read().decode("utf-8"))
    except (OSError, ValueError):
        return {}
    return {"titre": anonymiser(donnees.get("title") or "")}


def transcrire(source, modele_whisper: str = "small",
               langue: str | None = os.environ.get("VEILLE_LANGUE", "fr")) -> tuple[str, str | None]:
    """Transcrit un fichier audio/vidéo ou un tableau numpy (16 kHz mono). Renvoie (texte, langue).

    La langue est imposée (français par défaut, `VEILLE_LANGUE=auto` pour la détecter) : la
    détection automatique se trompe sur les sons difficiles. Whisper ne connaît pas le
    bambara : les passages en bambara sortent mal transcrits.
    """
    from faster_whisper import WhisperModel
    modele = WhisperModel(modele_whisper, device="cpu", compute_type="int8")
    segments, infos = modele.transcribe(source, vad_filter=True,
                                        language=None if langue in (None, "auto") else langue)
    texte = " ".join(s.text.strip() for s in segments)
    return texte, getattr(infos, "language", None)


def lignes_ocr(image, langues: str = "fra+eng") -> list[str]:
    """Texte d'une image (chemin ou PIL.Image), ligne par ligne, avec Tesseract."""
    import pytesseract
    from PIL import Image, ImageOps

    if not isinstance(image, Image.Image):
        image = Image.open(image)
    image = ImageOps.grayscale(image)
    # Le mode sombre de TikTok (texte clair sur fond noir) se lit mieux inversé.
    if sum(image.resize((1, 1)).getdata()) < 128:
        image = ImageOps.invert(image)
    if image.width < 1200:
        image = image.resize((image.width * 2, image.height * 2))
    texte = pytesseract.image_to_string(image, lang=langues, config="--psm 4")
    return texte.splitlines()


_COLONNES_TEXTE = ("texte", "text", "comment", "commentaire", "content", "message", "body")
_COLONNES_LIKES = ("likes", "like_count", "likecount", "digg_count", "reactions", "j'aime")


def lire_export_commentaires(chemin: Path) -> list[Commentaire]:
    """Lit un export CSV de commentaires fourni par le client.

    Seules la colonne de texte et celle des likes sont lues ; les autres (auteur, pseudo,
    identifiant…) sont ignorées et le texte est anonymisé.
    """
    with open(chemin, newline="", encoding="utf-8-sig") as f:
        lecteur = csv.DictReader(f, delimiter=_separateur(chemin))
        noms = {n.lower().strip(): n for n in (lecteur.fieldnames or [])}
        col_texte = next((noms[c] for c in _COLONNES_TEXTE if c in noms), None)
        if col_texte is None:
            raise ValueError(f"Aucune colonne de texte parmi {_COLONNES_TEXTE} dans {chemin}")
        col_likes = next((noms[c] for c in _COLONNES_LIKES if c in noms), None)
        commentaires = []
        for ligne in lecteur:
            texte = anonymiser(ligne.get(col_texte) or "")
            if texte:
                likes = lire_compteur(ligne.get(col_likes)) if col_likes else None
                commentaires.append(Commentaire(texte, likes))
    return commentaires


def _separateur(chemin: Path) -> str:
    with open(chemin, encoding="utf-8-sig") as f:
        entete = f.readline()
    return ";" if entete.count(";") > entete.count(",") else ","


def lire_stats(texte: str | None) -> dict:
    """« vues=12k,likes=1,2k,partages=300 » -> dict d'entiers (séparateur : virgule ou point-virgule)."""
    stats = {}
    for morceau in re.split(r"[;,]\s*(?=[a-zé]+\s*=)", texte or ""):
        if "=" in morceau:
            cle, valeur = morceau.split("=", 1)
            stats[cle.strip().lower()] = lire_compteur(valeur)
    return stats
