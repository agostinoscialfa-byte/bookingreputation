"""
dashboard.py
============
Genera la pagina web (il "cruscotto") come file HTML: data/dashboard.html
Basta aprirlo con doppio clic per vederlo nel browser.

Mostra, per ogni struttura:
  - il voto attuale (grande)
  - il confronto con la settimana scorsa (freccia verde/rossa)
  - il numero di recensioni
  - un grafico dello storico + la previsione dei prossimi mesi
  - quante recensioni servono per raggiungere il voto obiettivo
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from . import storage
from . import forecast

DASHBOARD_FILE = storage.DATA_DIR / "dashboard.html"


def _serie_storica(property_id: str) -> tuple[list[str], list[float]]:
    """Date e voti storici di una struttura, in ordine cronologico."""
    righe = sorted(
        (s for s in storage.leggi_storico() if s.property_id == property_id),
        key=lambda s: s.date,
    )
    return [s.date for s in righe], [s.score for s in righe]


def costruisci_dati_dashboard(config: dict) -> dict:
    """
    Prepara tutti i numeri che serviranno alla pagina.
    Restituisce un dizionario che poi trasformiamo in JSON per il grafico.
    """
    prev = config.get("previsione", {})
    rec_sett = float(prev.get("recensioni_a_settimana", 5))
    voto_nuove = float(prev.get("voto_medio_nuove_recensioni", 9.0))
    settimane = int(prev.get("settimane_da_proiettare", 12))
    obiettivo = float(prev.get("voto_obiettivo", 9.0))

    # Nomi leggibili dal config (id -> nome). Se manca, useremo il nome salvato.
    nomi = {s["id"]: s.get("nome", s["id"]) for s in config.get("strutture", [])}

    ultimi = storage.snapshot_piu_recenti()
    strutture_out = []

    for property_id, snap in sorted(ultimi.items(), key=lambda kv: kv[0]):
        nome = nomi.get(property_id, snap.property_name)

        # Confronto con ~7 giorni fa
        vecchio = storage.snapshot_di_circa_giorni_fa(property_id, 7)
        delta = round(snap.score - vecchio.score, 2) if vecchio else 0.0
        delta_rec = (snap.num_reviews - vecchio.num_reviews) if vecchio else 0

        # Previsione
        punti = forecast.proietta_voto(
            snap.score, snap.num_reviews, rec_sett, voto_nuove, settimane
        )
        voto_finale = punti[-1].voto_previsto
        servono = forecast.recensioni_per_obiettivo(
            snap.score, snap.num_reviews, voto_nuove, obiettivo
        )

        date_storiche, voti_storici = _serie_storica(property_id)

        strutture_out.append({
            "id": property_id,
            "nome": nome,
            "voto": snap.score,
            "recensioni": snap.num_reviews,
            "delta": delta,
            "delta_recensioni": delta_rec,
            "trend": forecast.descrivi_trend(delta),
            "ha_confronto": vecchio is not None,
            "voto_previsto_finale": voto_finale,
            "recensioni_per_obiettivo": servono,
            "storico_date": date_storiche,
            "storico_voti": voti_storici,
            "previsione_settimane": [p.settimana for p in punti],
            "previsione_voti": [p.voto_previsto for p in punti],
        })

    return {
        "generato_il": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "obiettivo": obiettivo,
        "settimane": settimane,
        "recensioni_a_settimana": rec_sett,
        "voto_medio_nuove": voto_nuove,
        "strutture": strutture_out,
    }


def genera_html(config: dict) -> Path:
    """Scrive il file data/dashboard.html e restituisce il suo percorso."""
    dati = costruisci_dati_dashboard(config)
    storage.DATA_DIR.mkdir(parents=True, exist_ok=True)
    html = _TEMPLATE.replace("/*DATI_JSON*/", json.dumps(dati, ensure_ascii=False))
    DASHBOARD_FILE.write_text(html, encoding="utf-8")
    return DASHBOARD_FILE


# ---------------------------------------------------------------------------
# Il template della pagina. E' HTML + un po' di JavaScript per i grafici.
# Il segnaposto /*DATI_JSON*/ viene sostituito con i dati veri qui sopra.
# ---------------------------------------------------------------------------
_TEMPLATE = r"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cruscotto Reputazione Booking</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
<style>
  :root { --verde:#0a8f3c; --rosso:#c62828; --grigio:#667085; --bordo:#e5e7eb; --blu:#0057b8; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
         background:#f5f7fb; color:#101828; }
  header { background:#003580; color:#fff; padding:20px 24px; }
  header h1 { margin:0; font-size:20px; }
  header p { margin:4px 0 0; opacity:.85; font-size:13px; }
  .wrap { max-width:1100px; margin:0 auto; padding:20px 16px 60px; }
  .griglia { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:16px; }
  .card { background:#fff; border:1px solid var(--bordo); border-radius:14px; padding:18px;
          box-shadow:0 1px 2px rgba(16,24,40,.04); }
  .nome { font-weight:600; font-size:15px; margin-bottom:10px; }
  .voto-riga { display:flex; align-items:baseline; gap:10px; }
  .voto { font-size:44px; font-weight:700; line-height:1; }
  .su10 { color:var(--grigio); font-size:14px; }
  .delta { font-size:14px; font-weight:600; padding:2px 8px; border-radius:999px; }
  .delta.su { background:#e7f6ec; color:var(--verde); }
  .delta.giu { background:#fde8e8; color:var(--rosso); }
  .delta.pari { background:#eef2f6; color:var(--grigio); }
  .meta { color:var(--grigio); font-size:13px; margin:8px 0 12px; }
  .box-prev { background:#f8fafc; border:1px solid var(--bordo); border-radius:10px;
              padding:10px 12px; font-size:13px; margin-bottom:12px; }
  .box-prev b { color:var(--blu); }
  canvas { width:100% !important; height:180px !important; }
  .nota { color:var(--grigio); font-size:12px; margin-top:24px; line-height:1.5; }
  .vuoto { background:#fff; border:1px dashed var(--bordo); border-radius:14px;
           padding:40px; text-align:center; color:var(--grigio); }
</style>
</head>
<body>
<header>
  <h1>Cruscotto Reputazione Booking</h1>
  <p id="sottotitolo"></p>
</header>
<div class="wrap">
  <div id="contenuto" class="griglia"></div>
  <div class="nota" id="nota"></div>
</div>

<script>
const DATI = /*DATI_JSON*/;

document.getElementById("sottotitolo").textContent =
  "Aggiornato il " + DATI.generato_il + " · obiettivo voto " + DATI.obiettivo;

const contenuto = document.getElementById("contenuto");

if (!DATI.strutture.length) {
  contenuto.className = "";
  contenuto.innerHTML = '<div class="vuoto">Nessun dato ancora. Lancia prima ' +
    'la raccolta dati (o la modalita\' demo) e poi rigenera il cruscotto.</div>';
}

DATI.strutture.forEach((s, i) => {
  const classeDelta = s.delta > 0 ? "su" : (s.delta < 0 ? "giu" : "pari");
  const freccia = s.delta > 0 ? "▲" : (s.delta < 0 ? "▼" : "▪");
  const segno = s.delta > 0 ? "+" : "";
  const testoDelta = s.ha_confronto
      ? (freccia + " " + segno + s.delta.toFixed(2) + " vs 7 gg fa")
      : "primo rilevamento";

  let testoObiettivo;
  if (s.recensioni_per_obiettivo === null) {
    testoObiettivo = "Con le ipotesi attuali il voto obiettivo non e\' raggiungibile "
                   + "(le nuove recensioni non spingono in quella direzione).";
  } else if (s.recensioni_per_obiettivo === 0) {
    testoObiettivo = "Sei gia\' al voto obiettivo. Bravo!";
  } else {
    testoObiettivo = "Per arrivare a <b>" + DATI.obiettivo + "</b> servono circa <b>"
                   + s.recensioni_per_obiettivo + "</b> nuove recensioni a voto "
                   + DATI.voto_medio_nuove + ".";
  }

  const card = document.createElement("div");
  card.className = "card";
  card.innerHTML =
    '<div class="nome">' + s.nome + '</div>' +
    '<div class="voto-riga">' +
      '<div class="voto">' + s.voto.toFixed(1) + '</div>' +
      '<div class="su10">/ 10</div>' +
      '<div class="delta ' + classeDelta + '">' + testoDelta + '</div>' +
    '</div>' +
    '<div class="meta">' + s.recensioni + ' recensioni' +
      (s.ha_confronto ? ' ( ' + (s.delta_recensioni>=0?"+":"") + s.delta_recensioni + ' nell\'ultima settimana )' : '') +
    '</div>' +
    '<div class="box-prev">Tra ' + DATI.settimane + ' settimane, mantenendo ' +
      DATI.recensioni_a_settimana + ' recensioni/sett. a voto ' + DATI.voto_medio_nuove +
      ', il voto stimato e\' <b>' + s.voto_previsto_finale.toFixed(2) + '</b>.<br>' +
      testoObiettivo + '</div>' +
    '<canvas id="grafico' + i + '"></canvas>';
  contenuto.appendChild(card);

  // Costruisco il grafico: prima lo storico reale, poi la previsione tratteggiata.
  const etichetteStorico = s.storico_date;
  const etichettePrev = s.previsione_settimane.map(w => "+" + w + " sett");
  // Le due serie condividono l'asse: attacco la previsione dopo lo storico.
  const labels = etichetteStorico.concat(etichettePrev.slice(1));

  const serieStorico = s.storico_voti.concat(new Array(Math.max(0, etichettePrev.length-1)).fill(null));
  const seriePrev = new Array(Math.max(0, etichetteStorico.length-1)).fill(null)
      .concat(s.previsione_voti);

  new Chart(document.getElementById("grafico"+i), {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        { label:"Storico", data:serieStorico, borderColor:"#003580",
          backgroundColor:"#003580", tension:.3, spanGaps:false, pointRadius:3 },
        { label:"Previsione", data:seriePrev, borderColor:"#0a8f3c",
          borderDash:[6,4], tension:.3, spanGaps:true, pointRadius:0 }
      ]
    },
    options: {
      responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{ display:true, labels:{ boxWidth:12, font:{size:11} } } },
      scales:{ y:{ suggestedMin: Math.max(0, s.voto-1), suggestedMax: 10,
                   ticks:{ font:{size:11} } },
               x:{ ticks:{ font:{size:10}, maxRotation:0, autoSkip:true } } }
    }
  });
});

document.getElementById("nota").innerHTML =
  "Nota: il voto Booking e\' la media dei voti delle singole recensioni. La previsione " +
  "ipotizza di mantenere lo stesso ritmo e la stessa qualita\' e serve come indicazione, " +
  "non come garanzia. Booking da\' meno peso alle recensioni molto vecchie: qui usiamo " +
  "una stima semplificata.";
</script>
</body>
</html>
"""
