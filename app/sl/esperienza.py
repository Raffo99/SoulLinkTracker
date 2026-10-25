"""Modalità "esperienza solo dagli allenatori": quanta esperienza dare in una lotta contro un allenatore.

Il gioco calcola l'esperienza come sempre; lo script la moltiplica per un numero intero N scelto qui
(0 = niente esperienza, come per i selvatici). N si sceglie in modo che il primo Pokémon della squadra
arrivi più o meno al livello del Pokémon più forte dell'allenatore, senza superare il level cap.
"""
import math

from . import logica as L

# curve di crescita (numerazione dei giochi): 0 medio-veloce, 1 irregolare, 2 fluttuante, 3 medio-lenta, 4 veloce, 5 lenta


def esp_per_livello(curva: int, n: int) -> int:
    """Esperienza totale per avere il livello n."""
    if n <= 1:
        return 0
    n3 = n ** 3
    if curva == 0:
        return n3
    if curva == 4:
        return 4 * n3 // 5
    if curva == 5:
        return 5 * n3 // 4
    if curva == 3:
        return max(0, 6 * n3 // 5 - 15 * n * n + 100 * n - 140)
    if curva == 1:                      # irregolare
        if n <= 50:
            return n3 * (100 - n) // 50
        if n <= 68:
            return n3 * (150 - n) // 100
        if n <= 98:
            return n3 * ((1911 - 10 * n) // 3) // 500
        return n3 * (160 - n) // 100
    if curva == 2:                      # fluttuante
        if n <= 15:
            return n3 * ((n + 1) // 3 + 24) // 50
        if n <= 36:
            return n3 * (n + 14) // 50
        return n3 * (n // 2 + 32) // 50
    return n3


def dati_specie(specie):
    v = (L._DATI.get("esperienza") or {}).get(str(specie))
    return (v[0], v[1]) if v else (0, 64)


def curva_di(specie, livello, esperienza):
    """Curva di crescita: quella della specie, a meno che l'esperienza attuale dica altro (randomizer)."""
    c, _ = dati_specie(specie)
    if esperienza is None:
        return c

    def coerente(k):
        return esp_per_livello(k, livello) <= esperienza < esp_per_livello(k, livello + 1) or livello >= 100
    if coerente(c):
        return c
    for k in (0, 3, 4, 5, 1, 2):
        if coerente(k):
            return k
    return c


def esp_normale(base, liv_nemico, liv_mio) -> float:
    """Esperienza che un Pokémon (unico partecipante) prende battendo un Pokémon di un allenatore (formula della 5ª gen)."""
    rapporto = ((2 * liv_nemico + 10) / (liv_nemico + liv_mio + 10)) ** 2.5
    return math.floor(1.5 * base * liv_nemico / 5 * rapporto) + 1


def moltiplicatore(nemici, primo, cap, dividi=1) -> dict:
    """nemici: [{specie, livello}], primo: {specie, livello, esperienza} (il primo Pokémon vivo della squadra).
    dividi: in quanti si dividono l'esperienza (con Condividi esperienza tutta la squadra viva)."""
    nemici = [n for n in nemici or [] if n.get("livello")]
    if not nemici or not primo:
        return {"n": 1, "obiettivo": None, "motivo": "dati mancanti"}
    obiettivo = min(max(n["livello"] for n in nemici), cap or 100)
    liv = primo.get("livello") or 1
    if liv >= obiettivo:
        return {"n": 0, "obiettivo": obiettivo, "motivo": "già al livello dell'allenatore"}
    curva = curva_di(primo.get("specie"), liv, primo.get("esperienza"))
    serve = esp_per_livello(curva, obiettivo) - (primo.get("esperienza") or esp_per_livello(curva, liv))
    normale = sum(esp_normale(dati_specie(n.get("specie"))[1], n["livello"], liv) for n in nemici) / max(1, dividi or 1)
    if serve <= 0:
        return {"n": 0, "obiettivo": obiettivo, "motivo": "già al livello dell'allenatore"}
    esp_ora = primo.get("esperienza") or esp_per_livello(curva, liv)

    def livello_finale(n):
        e = esp_ora + n * normale
        lv = liv
        while lv < 100 and esp_per_livello(curva, lv + 1) <= e:
            lv += 1
        return lv
    r = serve / max(1, normale)
    candidati = sorted({max(0, min(255, math.floor(r))), max(0, min(255, math.ceil(r)))})
    limite = min(cap or 100, obiettivo + 1)            # mai oltre il cap, al massimo un livello sopra l'allenatore
    validi = [n for n in candidati if livello_finale(n) <= limite] or [0]
    n = min(validi, key=lambda k: (abs(livello_finale(k) - obiettivo), k))
    return {"n": n, "obiettivo": obiettivo, "serve": serve, "normale": normale, "livello_previsto": livello_finale(n), "motivo": ""}
