"""Synthèse des fiches d'une marque, en Markdown (et CSV à plat pour un tableur).

    python -m veille.rapport --marque "Orange Mali"
"""

import argparse
import csv
from collections import Counter
from pathlib import Path

from .fiche import Fiche
from .pipeline import DOSSIER_DONNEES, lire_fiches


def rapport_markdown(fiches: list[Fiche], marque: str | None) -> str:
    titre = marque or "toutes marques"
    if not fiches:
        return f"# Veille : {titre}\n\nAucune fiche.\n"
    lus = sum(f.stats_commentaires.lus for f in fiches)
    l = [f"# Veille : {titre}", "",
         f"{len(fiches)} publications analysées, {lus} commentaires lus "
         f"(du {min(f.date_analyse for f in fiches)[:10]} au {max(f.date_analyse for f in fiches)[:10]}).", ""]

    l += ["## Sentiment des commentaires", "", "| Sentiment | Publications |", "|---|---|"]
    for s, n in Counter(f.sentiment_commentaires or "sans commentaire" for f in fiches).most_common():
        l.append(f"| {s} | {n} |")

    l += ["", "## Thèmes les plus fréquents", ""]
    l += [f"- {t} ({n})" for t, n in Counter(t.lower() for f in fiches for t in f.themes).most_common(10)]

    idees = sorted(((i, f) for f in fiches for i in f.idees_commentaires),
                   key=lambda p: p[0].likes_cumules, reverse=True)
    l += ["", "## Idées les plus soutenues (likes cumulés)", "",
          "| Idée | Sentiment | Commentaires | Likes | Publication |", "|---|---|---|---|---|"]
    for i, f in idees[:15]:
        l.append(f"| {i.idee} | {i.sentiment} | {i.nb_commentaires} | {i.likes_cumules} | [lien]({f.lien}) |")

    signaux = [(s, f) for f in fiches for s in f.signaux]
    if signaux:
        l += ["", "## Points d'attention", ""]
        l += [f"- {s} ([publication]({f.lien}))" for s, f in signaux]
    return "\n".join(l) + "\n"


def exporter_csv(fiches: list[Fiche], chemin: Path):
    """Une ligne par idée : facile à filtrer dans un tableur."""
    with open(chemin, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["date_analyse", "marque", "plateforme", "lien", "source", "sentiment_publication",
                    "vues", "likes_video", "partages", "commentaires_lus", "idee", "sentiment_idee",
                    "nb_commentaires", "likes_cumules"])
        for fi in fiches:
            base = [fi.date_analyse, fi.marque, fi.plateforme, fi.lien, fi.source, fi.sentiment_publication,
                    fi.stats_video.vues, fi.stats_video.likes, fi.stats_video.partages, fi.stats_commentaires.lus]
            for i in fi.idees_commentaires or [None]:
                w.writerow(base + ([i.idee, i.sentiment, i.nb_commentaires, i.likes_cumules] if i else ["", "", "", ""]))


def main(argv=None):
    p = argparse.ArgumentParser(description="Synthèse des fiches.")
    p.add_argument("--marque")
    p.add_argument("--donnees", type=Path, default=DOSSIER_DONNEES)
    a = p.parse_args(argv)
    fiches = [f for f in lire_fiches(a.donnees)
              if not a.marque or (f.marque or "").lower() == a.marque.lower()]
    nom = (a.marque or "toutes").replace(" ", "_")
    sortie = a.donnees / "rapports"
    sortie.mkdir(parents=True, exist_ok=True)
    (sortie / f"{nom}.md").write_text(rapport_markdown(fiches, a.marque), encoding="utf-8")
    exporter_csv(fiches, sortie / f"{nom}.csv")
    print(f"Rapport : {sortie / (nom + '.md')} ; tableur : {sortie / (nom + '.csv')}")


if __name__ == "__main__":
    main()
