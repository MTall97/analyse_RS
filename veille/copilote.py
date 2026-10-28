"""Module 1 : le copilote de l'analyste.

L'analyste navigue lui-même sur TikTok (téléphone recopié à l'écran, ou site web). Le
copilote, sur son PC :
- lit les commentaires visibles dans une zone de l'écran choisie (OCR local) ;
- écoute le son de la vidéo (son du PC) et le transcrit en local ;
- à la fin, envoie à l'analyse les textes anonymisés et enregistre la fiche.

Les captures, le son, la transcription et les commentaires restent en mémoire et sont
effacés après chaque fiche : seule la fiche est écrite.

    python -m veille.copilote
"""

import json
import sys
import threading
from pathlib import Path

from .analyse import ClaudeModele, Entree
from .fiche import StatsVideo
from .nombres import lire_compteur
from .ocr_tiktok import fusionner, lire_commentaires
from .pipeline import DOSSIER_DONNEES, enregistrer, produire_fiche
from .sources import infos_publiques, lignes_ocr, plateforme, transcrire

REGLAGES = Path.home() / ".veille_avis.json"
TESSERACT_WINDOWS = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


class Session:
    """Ce qui est accumulé pour une publication, sans interface (testable)."""

    def __init__(self, ocr=lignes_ocr, transcrire=transcrire, infos=infos_publiques):
        self._ocr, self._transcrire, self._infos = ocr, transcrire, infos
        self.vider()

    def vider(self):
        self.commentaires = []
        self.transcription = None
        self.ignores = 0

    def lire_ecran(self, image) -> int:
        """Ajoute les commentaires d'une capture ; renvoie le nombre de nouveaux."""
        avant = len(self.commentaires)
        nouveaux, ignores = lire_commentaires(self._ocr(image))
        fusionner(self.commentaires, nouveaux)
        self.ignores += ignores
        return len(self.commentaires) - avant

    def ajouter_audio(self, audio_16k):
        texte, _ = self._transcrire(audio_16k)
        self.transcription = " ".join(t for t in (self.transcription, texte) if t)

    def terminer(self, lien: str, marque: str | None, stats: StatsVideo, modele, notes: str | None = None,
                 dossier: Path = DOSSIER_DONNEES):
        contexte = [self._infos(lien).get("titre") if lien else None, notes]
        entree = Entree(plateforme=plateforme(lien), marque=marque,
                        contexte="\n".join(c for c in contexte if c) or None,
                        transcription=self.transcription, commentaires=self.commentaires)
        fiche = produire_fiche(entree, lien, "copilote", modele, stats)
        enregistrer(fiche, dossier)
        self.vider()
        return fiche


class Ecoute:
    """Enregistre le son du PC (boucle de sortie WASAPI sous Windows) jusqu'à `arreter`."""

    TAUX = 48_000

    def __init__(self):
        self._blocs, self._stop = [], threading.Event()
        self._fil = threading.Thread(target=self._enregistrer, daemon=True)
        self.erreur = None

    def demarrer(self):
        self._fil.start()

    def _enregistrer(self):
        try:
            import soundcard as sc
            sortie = sc.default_speaker()
            micro = sc.get_microphone(str(sortie.name), include_loopback=True)
            with micro.recorder(samplerate=self.TAUX, channels=1) as r:
                while not self._stop.is_set():
                    self._blocs.append(r.record(numframes=self.TAUX // 4))
        except Exception as e:  # pas de carte son, autre système…
            self.erreur = e

    def arreter(self):
        """Renvoie le son en 16 kHz mono (format attendu par Whisper), ou None."""
        import numpy as np
        self._stop.set()
        self._fil.join(timeout=2)
        if not self._blocs:
            return None
        son = np.concatenate(self._blocs).reshape(-1).astype("float32")
        son = son[: len(son) // 3 * 3].reshape(-1, 3).mean(axis=1)  # 48 kHz -> 16 kHz
        return son


def capturer(zone):
    import mss
    from PIL import Image
    x, y, l, h = zone
    with mss.mss() as ecran:
        brut = ecran.grab({"left": x, "top": y, "width": l, "height": h})
    return Image.frombytes("RGB", brut.size, brut.rgb)


def lire_reglages() -> dict:
    try:
        return json.loads(REGLAGES.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def ecrire_reglages(reglages: dict):
    REGLAGES.write_text(json.dumps(reglages), encoding="utf-8")


def application():
    import tkinter as tk
    from tkinter import messagebox

    if sys.platform == "win32":
        import ctypes
        try:  # coordonnées Tk = pixels réels de l'écran, comme pour la capture
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            pass
        if TESSERACT_WINDOWS.exists():
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_WINDOWS)

    reglages = lire_reglages()
    session = Session()
    modele = ClaudeModele()
    etat = {"ecoute": None}

    racine = tk.Tk()
    racine.title("Copilote de veille")
    racine.attributes("-topmost", True)
    police = ("Segoe UI", 11)

    def champ(texte, ligne, largeur=34):
        tk.Label(racine, text=texte, font=police).grid(row=ligne, column=0, sticky="w", padx=6, pady=2)
        e = tk.Entry(racine, width=largeur, font=police)
        e.grid(row=ligne, column=1, columnspan=2, sticky="we", padx=6, pady=2)
        return e

    marque = champ("Marque", 0)
    marque.insert(0, reglages.get("marque", ""))
    lien = champ("Lien", 1)
    tk.Button(racine, text="Coller", command=lambda: (lien.delete(0, "end"),
              lien.insert(0, racine.clipboard_get().strip()))).grid(row=1, column=3, padx=4)
    stats = {nom: champ(f"{nom.capitalize()} (vidéo)", 2 + i, 12)
             for i, nom in enumerate(StatsVideo.model_fields)}
    notes = champ("Notes", 7)
    statut = tk.Label(racine, text="Choisissez la zone des commentaires.", font=police, fg="#555")
    statut.grid(row=9, column=0, columnspan=4, sticky="w", padx=6)
    resultat = tk.Text(racine, width=60, height=12, font=("Consolas", 9))
    resultat.grid(row=10, column=0, columnspan=4, padx=6, pady=6)

    def afficher():
        mots = len((session.transcription or "").split())
        statut.config(text=f"{len(session.commentaires)} commentaires lus · {mots} mots transcrits"
                           f" · {session.ignores} blocs ignorés")

    def choisir_zone():
        voile = tk.Toplevel(racine)
        voile.attributes("-fullscreen", True)
        voile.attributes("-alpha", 0.3)
        voile.attributes("-topmost", True)
        toile = tk.Canvas(voile, cursor="cross", bg="black")
        toile.pack(fill="both", expand=True)
        depart = {}

        def appui(ev):
            depart.update(x=ev.x_root, y=ev.y_root, cx=ev.x, cy=ev.y)
            depart["rect"] = toile.create_rectangle(ev.x, ev.y, ev.x, ev.y, outline="red", width=3)

        def glisse(ev):
            toile.coords(depart["rect"], depart["cx"], depart["cy"], ev.x, ev.y)

        def relache(ev):
            x, y = min(depart["x"], ev.x_root), min(depart["y"], ev.y_root)
            l, h = abs(ev.x_root - depart["x"]), abs(ev.y_root - depart["y"])
            voile.destroy()
            if l > 50 and h > 50:
                reglages["zone"] = [x, y, l, h]
                ecrire_reglages(reglages)
                statut.config(text="Zone enregistrée. Ouvrez les commentaires puis « Lire l'écran ».")

        toile.bind("<ButtonPress-1>", appui)
        toile.bind("<B1-Motion>", glisse)
        toile.bind("<ButtonRelease-1>", relache)
        voile.bind("<Escape>", lambda ev: voile.destroy())

    def lire_ecran():
        if "zone" not in reglages:
            return choisir_zone()
        racine.withdraw()  # la fenêtre du copilote ne doit pas cacher les commentaires
        racine.after(250, _lire)

    def _lire():
        try:
            nouveaux = session.lire_ecran(capturer(reglages["zone"]))
        except Exception as e:
            racine.deiconify()
            return messagebox.showerror("Lecture", f"Lecture impossible : {e}")
        racine.deiconify()
        afficher()
        statut.config(text=statut.cget("text") + f" (+{nouveaux}). Faites défiler et relisez.")

    def ecouter():
        if etat["ecoute"] is None:
            etat["ecoute"] = Ecoute()
            etat["ecoute"].demarrer()
            bouton_ecoute.config(text="Arrêter l'écoute")
            statut.config(text="Écoute du son du PC… Lancez la vidéo.")
            return
        ecoute, etat["ecoute"] = etat["ecoute"], None
        bouton_ecoute.config(text="Écouter la vidéo")
        son = ecoute.arreter()
        if ecoute.erreur or son is None:
            return messagebox.showerror("Écoute", f"Pas de son enregistré : {ecoute.erreur}")
        statut.config(text="Transcription en cours…")

        def travail():
            session.ajouter_audio(son)
            racine.after(0, afficher)
        threading.Thread(target=travail, daemon=True).start()

    def terminer():
        if not lien.get().strip():
            return messagebox.showwarning("Fiche", "Collez le lien de la publication.")
        valeurs = {nom: lire_compteur(e.get()) for nom, e in stats.items()}
        reglages["marque"] = marque.get().strip()
        ecrire_reglages(reglages)
        statut.config(text="Analyse en cours…")

        def travail():
            try:
                fiche = session.terminer(lien.get().strip(), reglages["marque"] or None,
                                         StatsVideo(**valeurs), modele, notes.get().strip() or None)
            except Exception as e:
                return racine.after(0, lambda: messagebox.showerror("Analyse", str(e)))
            racine.after(0, lambda: fin(fiche))
        threading.Thread(target=travail, daemon=True).start()

    def fin(fiche):
        resultat.delete("1.0", "end")
        resultat.insert("end", fiche.resume_publication + "\n\n")
        for i in fiche.idees_commentaires:
            resultat.insert("end", f"- [{i.sentiment}] {i.idee} ({i.nb_commentaires} comm., {i.likes_cumules} likes)\n")
        for s in fiche.signaux:
            resultat.insert("end", f"! {s}\n")
        for e in [lien, notes, *stats.values()]:
            e.delete(0, "end")
        statut.config(text="Fiche enregistrée. Publication suivante.")

    def annuler():
        if etat["ecoute"]:
            etat["ecoute"].arreter()
            etat["ecoute"] = None
            bouton_ecoute.config(text="Écouter la vidéo")
        session.vider()
        afficher()

    boutons = tk.Frame(racine)
    boutons.grid(row=8, column=0, columnspan=4, pady=6)
    for texte, action in (("Zone des commentaires", choisir_zone), ("Lire l'écran", lire_ecran)):
        tk.Button(boutons, text=texte, font=police, command=action).pack(side="left", padx=3)
    bouton_ecoute = tk.Button(boutons, text="Écouter la vidéo", font=police, command=ecouter)
    bouton_ecoute.pack(side="left", padx=3)
    tk.Button(boutons, text="Terminer la fiche", font=police, bg="#d8f0d8", command=terminer).pack(side="left", padx=3)
    tk.Button(boutons, text="Annuler", font=police, command=annuler).pack(side="left", padx=3)

    racine.mainloop()


if __name__ == "__main__":
    application()
