"""Aggiornamento automatico: controlla l'ultima versione pubblicata su GitHub (Releases), scarica il nuovo exe,
lo mette al posto di quello attuale e riavvia l'app.

Funziona con una repo pubblica (le Release di una repo privata non si vedono senza credenziali)."""
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from . import VERSIONE

REPO = "Raffo99/SoulLinkTracker"
API = "https://api.github.com/repos/{repo}/releases/latest"
NOME_EXE = "SoulLinkTracker.exe"
UA = "SoulLinkTracker-Aggiornamento"


class ErroreAggiornamento(Exception):
    pass


def numero(v: str) -> tuple:
    """'v4.10.2' -> (4, 10, 2) per confrontare le versioni."""
    return tuple(int(x) for x in re.findall(r"\d+", v or "")[:4]) or (0,)


def e_exe() -> bool:
    """L'app gira come exe (PyInstaller)? Da sorgente non c'è niente da sostituire."""
    return bool(getattr(sys, "frozen", False))


def controlla(repo: str = REPO, api: str = API, versione_attuale: str = VERSIONE) -> dict | None:
    """Restituisce le informazioni sulla versione nuova, oppure None se sei già all'ultima."""
    req = urllib.request.Request(api.format(repo=repo), headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            dati = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ErroreAggiornamento("Non trovo versioni pubblicate: la repo deve essere pubblica e avere almeno una Release.")
        if e.code == 403:
            raise ErroreAggiornamento("GitHub ha rifiutato la richiesta (troppi controlli ravvicinati): riprova più tardi.")
        raise ErroreAggiornamento(f"Errore di GitHub {e.code}.")
    except urllib.error.URLError as e:
        raise ErroreAggiornamento(f"GitHub non raggiungibile: {e.reason}")
    tag = dati.get("tag_name") or ""
    if numero(tag) <= numero(versione_attuale):
        return None
    asset = next((a for a in dati.get("assets") or [] if a.get("name", "").lower() == NOME_EXE.lower()), None)
    if not asset:
        raise ErroreAggiornamento(f"La versione {tag} non contiene {NOME_EXE}.")
    digest = asset.get("digest") or ""
    return {"versione": tag.lstrip("vV"), "tag": tag, "note": (dati.get("body") or "").strip(),
            "url": asset["browser_download_url"], "dimensione": asset.get("size") or 0,
            "sha256": digest.split(":", 1)[1].lower() if digest.startswith("sha256:") else None,
            "pagina": dati.get("html_url") or ""}


def cartella_exe() -> Path:
    return Path(sys.executable).resolve().parent


def scarica(info: dict, avanzamento=None, cartella: Path | None = None, fermo=lambda: False) -> Path:
    """Scarica il nuovo exe accanto a quello attuale e lo controlla (dimensione, formato, impronta SHA-256)."""
    cartella = cartella or cartella_exe()
    dest = cartella / "SoulLinkTracker.nuovo.exe"
    req = urllib.request.Request(info["url"], headers={"User-Agent": UA, "Accept": "application/octet-stream"})
    h = hashlib.sha256()
    letti = 0
    try:
        with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
            totale = int(r.headers.get("Content-Length") or info.get("dimensione") or 0)
            while True:
                if fermo():
                    raise ErroreAggiornamento("Scaricamento annullato.")
                blocco = r.read(256 * 1024)
                if not blocco:
                    break
                f.write(blocco)
                h.update(blocco)
                letti += len(blocco)
                if avanzamento:
                    avanzamento(letti, totale)
    except (urllib.error.URLError, OSError) as e:
        dest.unlink(missing_ok=True)
        if isinstance(e, ErroreAggiornamento):
            raise
        raise ErroreAggiornamento(f"Scaricamento non riuscito: {e}")
    except ErroreAggiornamento:
        dest.unlink(missing_ok=True)
        raise
    problema = None
    if info.get("dimensione") and letti != info["dimensione"]:
        problema = "il file scaricato è incompleto"
    elif dest.read_bytes()[:2] != b"MZ":
        problema = "il file scaricato non è un programma Windows"
    elif info.get("sha256") and h.hexdigest() != info["sha256"]:
        problema = "l'impronta del file non corrisponde a quella pubblicata"
    if problema:
        dest.unlink(missing_ok=True)
        raise ErroreAggiornamento(f"Aggiornamento annullato: {problema}.")
    return dest


def installa(nuovo: Path) -> Path:
    """Mette il nuovo exe al posto di quello in uso (su Windows un exe aperto si può rinominare, non sovrascrivere)."""
    attuale = Path(sys.executable).resolve()
    vecchio = attuale.with_name("SoulLinkTracker.vecchio.exe")
    try:
        if vecchio.exists():
            vecchio.unlink()
        attuale.rename(vecchio)
    except OSError as e:
        raise ErroreAggiornamento(f"Non posso sostituire l'exe in {attuale.parent} ({e}). "
                                  "Spostalo in una cartella tua (per esempio Documenti) e riprova.")
    try:
        nuovo.rename(attuale)
    except OSError as e:
        vecchio.rename(attuale)                 # rimetti tutto com'era
        raise ErroreAggiornamento(f"Non posso installare la nuova versione: {e}")
    return attuale


def riavvia(exe: Path):
    """Avvia il nuovo exe come programma indipendente (non deve riusare i file temporanei di quello vecchio)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("_PYI", "_MEI"))}
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([str(exe), "--aggiornato"], cwd=str(exe.parent), env=env, creationflags=flags, close_fds=True)


def pulisci():
    """All'avvio: toglie l'exe vecchio e scaricamenti a metà rimasti da un aggiornamento precedente."""
    if not e_exe():
        return
    for nome in ("SoulLinkTracker.vecchio.exe", "SoulLinkTracker.nuovo.exe"):
        try:
            (cartella_exe() / nome).unlink(missing_ok=True)
        except OSError:
            pass                                 # il vecchio processo sta ancora chiudendo: ci si riprova la prossima volta


def note_brevi(note: str, righe=12) -> str:
    out = [r.rstrip() for r in (note or "").splitlines() if r.strip()]
    testo = "\n".join(out[:righe])
    return testo + ("\n…" if len(out) > righe else "")
