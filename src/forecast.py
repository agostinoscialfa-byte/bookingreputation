"""
forecast.py
===========
Calcola la PREVISIONE del voto Booking.

COME FUNZIONA IL VOTO DI BOOKING (in modo semplice):
il voto che vedi (es. 8.7) e' sostanzialmente la MEDIA dei voti delle
singole recensioni (ognuna da 1 a 10). Quindi, se oggi hai:
   - voto medio S su N recensioni
e nei prossimi mesi arrivano nuove recensioni con voto medio L,
il nuovo voto si sposta cosi' (media pesata):

        nuovo_voto = (S * N  +  L * k) / (N + k)

dove k = numero di NUOVE recensioni.

Piu' recensioni hai gia' (N grande), piu' il voto e' "pesante" da muovere:
una singola recensione brutta pesa poco su 2000 recensioni, ma tantissimo
su 20. Questo modello lo rende evidente.

NOTA ONESTA: Booking usa anche una "finestra temporale" (le recensioni molto
vecchie contano meno). Senza la data di ogni singola recensione non possiamo
riprodurlo al 100%. Questo modello e' un'ottima approssimazione per rispondere
alla domanda "se continuo cosi', dove va il mio voto?".
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PuntoPrevisione:
    settimana: int          # 0 = oggi, 1 = tra una settimana, ...
    voto_previsto: float    # voto stimato in quella settimana
    recensioni_totali: int  # quante recensioni avrai in totale


def proietta_voto(
    voto_attuale: float,
    recensioni_attuali: int,
    recensioni_a_settimana: float,
    voto_medio_nuove: float,
    settimane: int,
) -> list[PuntoPrevisione]:
    """
    Restituisce l'andamento previsto del voto, settimana per settimana,
    ipotizzando di mantenere lo stesso ritmo e la stessa qualita'.
    """
    punti: list[PuntoPrevisione] = [
        PuntoPrevisione(0, round(voto_attuale, 2), recensioni_attuali)
    ]

    somma_voti = voto_attuale * recensioni_attuali  # "punti totali" accumulati
    n = recensioni_attuali

    for settimana in range(1, settimane + 1):
        nuove = recensioni_a_settimana
        somma_voti += voto_medio_nuove * nuove
        n += nuove
        voto = somma_voti / n if n > 0 else voto_attuale
        punti.append(PuntoPrevisione(settimana, round(voto, 2), int(round(n))))

    return punti


def recensioni_per_obiettivo(
    voto_attuale: float,
    recensioni_attuali: int,
    voto_medio_nuove: float,
    voto_obiettivo: float,
) -> int | None:
    """
    Quante nuove recensioni (al voto medio ipotizzato) servono per raggiungere
    il voto obiettivo? Restituisce None se e' impossibile con quelle ipotesi.

    Esempi di 'impossibile':
      - vuoi salire ma le nuove recensioni valgono MENO del voto obiettivo
      - vuoi scendere ma le nuove valgono PIU' dell'obiettivo
    """
    if abs(voto_attuale - voto_obiettivo) < 1e-9:
        return 0  # ci sei gia'

    vuoi_salire = voto_obiettivo > voto_attuale
    # Se le nuove recensioni non "spingono" nella direzione giusta, non arrivi mai.
    if vuoi_salire and voto_medio_nuove <= voto_obiettivo:
        return None
    if not vuoi_salire and voto_medio_nuove >= voto_obiettivo:
        return None

    # Risolvo (S*N + L*k)/(N+k) = T  rispetto a k:
    #   k = N * (T - S) / (L - T)
    S, N, L, T = voto_attuale, recensioni_attuali, voto_medio_nuove, voto_obiettivo
    k = N * (T - S) / (L - T)
    if k < 0:
        return None
    return int(k) + 1  # arrotondo per eccesso: serve "almeno" questo numero


def descrivi_trend(delta: float) -> str:
    """Piccola etichetta testuale per il confronto settimanale."""
    if delta > 0.001:
        return "in salita"
    if delta < -0.001:
        return "in discesa"
    return "stabile"
