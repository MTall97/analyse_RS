"""Analyse, fiche et parcours complet, avec un modèle factice (aucun appel réseau)."""

import csv
import json
from types import SimpleNamespace

import pytest

from veille.analyse import AnalyseBrute, ClaudeModele, Entree, IdeeBrute, analyser, construire_message
from veille.client import preparer_entree
from veille.copilote import Session
from veille.fiche import Commentaire, StatsVideo
from veille.pipeline import enregistrer, lire_fiches, produire_fiche
from veille.rapport import rapport_markdown
from veille.sources import infos_publiques, lire_stats, plateforme

COMMENTAIRES = [
    Commentaire("Le forfait internet est vraiment trop cher pour les étudiants ici", 120),
    Commentaire("Franchement le prix a encore augmenté ce mois", 30),
    Commentaire("Réseau parfait à Sikasso, rien à dire", 5),
]


class Factice:
    def __init__(self, brute):
        self.brute, self.messages = brute, []

    def analyser(self, message):
        self.messages.append(message)
        return self.brute


def brute(idees, signaux=()):
    return AnalyseBrute(resume_publication="Vidéo promotionnelle d'un nouveau forfait.",
                        themes=["prix", "réseau"], sentiment_publication="positif",
                        sentiment_commentaires="mitige", idees=idees, signaux=list(signaux),
                        langues=["français"])


def test_comptes_calcules_et_citations_retirees():
    modele = Factice(brute([
        IdeeBrute(idee="Prix jugé trop élevé, surtout pour les jeunes", sentiment="negatif", commentaires=[1, 2, 2, 9]),
        IdeeBrute(idee="Bonne couverture réseau en région", sentiment="positif", commentaires=[3]),
        IdeeBrute(idee="le forfait internet est vraiment trop cher pour", sentiment="negatif", commentaires=[1]),
        IdeeBrute(idee="Voir le compte @client_mecontent", sentiment="negatif", commentaires=[2]),
    ], signaux=["Plainte récurrente sur le prix", "Contacter @quelquun"]))
    r = analyser(Entree("tiktok", "MarqueX", commentaires=COMMENTAIRES), modele)
    assert [(i.idee, i.nb_commentaires, i.likes_cumules) for i in r.idees] == [
        ("Prix jugé trop élevé, surtout pour les jeunes", 2, 150),
        ("Bonne couverture réseau en région", 1, 5)]
    assert r.idees[0].part_commentaires == pytest.approx(0.667)
    assert r.signaux == ["Plainte récurrente sur le prix"]
    assert r.idees_retirees == 3
    assert "[c1] (likes : 120)" in modele.messages[0]


def test_fiche_enregistree_sans_texte_de_commentaire(tmp_path):
    modele = Factice(brute([IdeeBrute(idee="Prix jugé trop élevé", sentiment="negatif", commentaires=[1, 2])]))
    entree = Entree("tiktok", "MarqueX", transcription="Découvrez notre offre", commentaires=COMMENTAIRES)
    fiche = produire_fiche(entree, "https://www.tiktok.com/@marquex/video/1", "client", modele,
                           StatsVideo(vues=12000, likes=800))
    enregistrer(fiche, tmp_path)
    contenu = (tmp_path / "fiches.jsonl").read_text(encoding="utf-8")
    for c in COMMENTAIRES:
        assert c.texte not in contenu
    assert "Découvrez notre offre" not in contenu
    relue = lire_fiches(tmp_path)[0]
    assert relue.stats_commentaires.lus == 3 and relue.stats_commentaires.likes_total == 155
    assert relue.stats_commentaires.likes_median == 30 and relue.transcription_disponible
    assert "Prix jugé trop élevé" in rapport_markdown([relue], "MarqueX")


def test_export_client_sans_auteur(tmp_path):
    export = tmp_path / "export.csv"
    with open(export, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Auteur", "Texte", "Likes"])
        w.writerow(["Aminata Traoré", "Livraison rapide, merci @aminata_t", "1,5k"])
        w.writerow(["Oumar K.", "", "3"])
    entree = preparer_entree("https://www.tiktok.com/@marque/video/2", "Marque", commentaires=export,
                             infos=lambda lien: {"titre": "Nouvelle offre"})
    assert [(c.texte, c.likes) for c in entree.commentaires] == [("Livraison rapide, merci [pseudo]", 1500)]
    assert entree.contexte == "Nouvelle offre"
    assert "Aminata" not in construire_message(entree)


def test_session_copilote(tmp_path):
    captures = {"a": ["kadi", "Trop cher", "1j Répondre 4"], "b": ["kadi", "Trop cher", "1j Répondre 6",
                                                                      "sidi", "Super pub", "2h Répondre"]}
    s = Session(ocr=lambda image: captures[image], transcrire=lambda son: ("bonjour à tous", "fr"),
                infos=lambda lien: {})
    assert s.lire_ecran("a") == 1 and s.lire_ecran("b") == 1
    s.ajouter_audio(object())
    modele = Factice(brute([IdeeBrute(idee="Prix critiqué", sentiment="negatif", commentaires=[1])]))
    fiche = s.terminer("https://www.tiktok.com/@m/video/3", "M", StatsVideo(), modele, dossier=tmp_path)
    assert fiche.source == "copilote" and fiche.idees_commentaires[0].likes_cumules == 6
    assert s.commentaires == [] and s.transcription is None  # rien ne reste en mémoire


def test_refus_signale():
    reponse = SimpleNamespace(stop_reason="refusal", parsed_output=None)
    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(parse=lambda **k: reponse)))
    with pytest.raises(RuntimeError, match="refusé"):
        ClaudeModele(client=client).analyser("...")


def test_requete_claude():
    vus = {}

    def parse(**k):
        vus.update(k)
        return SimpleNamespace(stop_reason="end_turn", parsed_output=brute([]))
    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(parse=parse)))
    ClaudeModele(client=client).analyser("message")
    assert vus["output_format"] is AnalyseBrute and vus["fallbacks"] == "default"
    assert vus["model"] == "claude-opus-5-5"


def test_sources():
    assert plateforme("https://vm.tiktok.com/abc") == "tiktok"
    assert plateforme("https://youtu.be/xyz") == "youtube"
    assert lire_stats("vues=12k;likes=1,2k;partages=85") == {"vues": 12000, "likes": 1200, "partages": 85}

    class Reponse:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def read(self): return json.dumps({"title": "Promo @createur", "author_name": "x"}).encode()
    vues = []
    infos = infos_publiques("https://www.tiktok.com/@m/video/1", ouvrir=lambda r, timeout: vues.append(r.full_url) or Reponse())
    assert infos == {"titre": "Promo [pseudo]"}
    assert vues[0].startswith("https://www.tiktok.com/oembed?url=https%3A%2F%2F")
    assert infos_publiques("https://exemple.ml/page") == {}
