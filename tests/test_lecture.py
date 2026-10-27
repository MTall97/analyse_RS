"""Compteurs, anonymisation et lecture des captures. Pseudos et commentaires inventés."""

from veille.confidentialite import anonymiser, contient_citation, contient_identifiant
from veille.nombres import lire_compteur
from veille.ocr_tiktok import fusionner, lire_commentaires
from veille.fiche import Commentaire


def test_compteurs():
    assert lire_compteur("12,3 k") == 12_300
    assert lire_compteur("12.3K") == 12_300
    assert lire_compteur("1,2M") == 1_200_000
    assert lire_compteur("1 234") == 1234
    assert lire_compteur("1.234") == 1234
    assert lire_compteur("45") == 45
    assert lire_compteur("j'aime") is None
    assert lire_compteur("") is None


def test_anonymiser():
    t = anonymiser("Merci @awa.k223 ! Appelez le +223 70 00 00 00 ou ecrivez a test@exemple.ml, https://x.y/z")
    assert "awa" not in t and "70 00" not in t and "test@" not in t and "https" not in t
    assert "[pseudo]" in t and "[téléphone]" in t and "[courriel]" in t and "[lien]" in t


def test_citation_et_identifiant():
    commentaires = ["Le réseau coupe tous les soirs dans mon quartier depuis une semaine"]
    assert contient_citation("Selon eux, le réseau coupe tous les soirs dans mon quartier", commentaires)
    assert not contient_citation("Coupures du réseau le soir signalées", commentaires)
    assert contient_identifiant("comme le dit @moussa")
    assert not contient_identifiant("Les clients d'Orange se plaignent du prix")


LIGNES_CAPTURE = [
    "345 commentaires",
    "kadi_bamako",
    "Le forfait est trop cher pour ce qu'on a",
    "2j Répondre ♡ 1,2k",
    "Voir 14 réponses",
    "issa.officiel",
    "Moi ça marche bien à Kalaban",
    "depuis le mois dernier",
    "5h Répondre",
    "87",
    "fanta77",
    "il y a 5 ans que je suis client",
    "il y a 3 j · Répondre 12",
    "coupé_en_bas",
]


def test_lire_commentaires_sans_pseudo():
    commentaires, ignores = lire_commentaires(LIGNES_CAPTURE)
    textes = [c.texte for c in commentaires]
    assert textes == ["Le forfait est trop cher pour ce qu'on a",
                      "Moi ça marche bien à Kalaban depuis le mois dernier",
                      "il y a 5 ans que je suis client"]
    assert [c.likes for c in commentaires] == [1200, 87, 12]
    assert ignores == 1  # le bloc coupé en bas de l'écran
    tout = " ".join(textes)
    for pseudo in ("kadi_bamako", "issa.officiel", "fanta77", "coupé_en_bas"):
        assert pseudo not in tout


def test_entete_non_reconnu_ne_fait_pas_fuiter_le_pseudo():
    # Une ligne d'interface inconnue avant le premier pseudo décale le bloc d'une ligne.
    commentaires, _ = lire_commentaires(["Trier par pertinence", "kadi_bamako", "Trop cher", "2j Répondre"])
    assert [c.texte for c in commentaires] == ["Trop cher"]
    commentaires, _ = lire_commentaires(["1 245 commentaires", "kadi_bamako", "Trop cher", "2j Répondre"])
    assert [c.texte for c in commentaires] == ["Trop cher"]


def test_bloc_d_une_ligne_ignore():
    commentaires, ignores = lire_commentaires(["pseudo_seul", "1j Répondre"])
    assert commentaires == [] and ignores == 1


def test_fusion_sans_doublon():
    a = [Commentaire("Trop cher !", 10)]
    fusionner(a, [Commentaire("trop cher", 15), Commentaire("Service rapide", None)])
    assert [(c.texte, c.likes) for c in a] == [("Trop cher !", 15), ("Service rapide", None)]
