"""
dashboard.py
============
Genera la pagina web (il "cruscotto") come file HTML: data/dashboard.html

Per ogni struttura mostra, usando il tuo modello (EWMA):
  - il voto calcolato oggi + confronto con la settimana scorsa (dallo storico)
  - ritmo ultimi 3 mesi, media 7/30 giorni, n. recensioni, recensioni/mese
  - il verdetto (sale / scende / stabile) e i "gradini" con le date
  - il grafico storico + proiezione a 24 mesi
  - la tabella dei sottoreparti (Pulizia, Personale, ecc.)

I numeri della proiezione arrivano dall'ultimo file scaricato in data/downloads/
(che contiene TUTTE le recensioni con le date). Il confronto settimanale arriva
dallo storico giornaliero (data/history.csv).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from . import storage
from . import modello_booking

DASHBOARD_FILE = storage.DATA_DIR / "dashboard.html"
DOWNLOAD_DIR = storage.DATA_DIR / "downloads"


def _ultimo_file_recensioni(hotel_id: str) -> Path | None:
    """Trova il file di recensioni piu' recente per un hotel_id (nome: DATA_hotelid.ext)."""
    if not hotel_id or not DOWNLOAD_DIR.exists():
        return None
    candidati = sorted(
        list(DOWNLOAD_DIR.glob(f"*_{hotel_id}.csv"))
        + list(DOWNLOAD_DIR.glob(f"*_{hotel_id}.xlsx")),
        key=lambda p: p.name,
    )
    return candidati[-1] if candidati else None


def _dati_struttura(struttura: dict) -> dict | None:
    """Prepara tutti i numeri di UNA struttura per il cruscotto."""
    pid = struttura["id"]
    nome = struttura.get("nome", pid)
    hotel_id = str(struttura.get("hotel_id", ""))

    # 1) Analisi completa dall'ultimo file di recensioni (se c'e').
    analisi = None
    file_rec = _ultimo_file_recensioni(hotel_id)
    if file_rec is not None:
        try:
            analisi = modello_booking.analizza_file(file_rec)
        except Exception as e:
            print(f"  (nota: analisi fallita per {nome}: {e})")

    # 2) Snapshot piu' recente dallo storico (per numeri correnti e confronto).
    ultimi = storage.snapshot_piu_recenti()
    snap = ultimi.get(pid)

    if analisi is None and snap is None:
        return None  # niente da mostrare per questa struttura

    calc = analisi.calc if analisi else (snap.score if snap else 0)
    n_tot = analisi.n_totali if analisi else (snap.num_reviews if snap else 0)
    pace = analisi.pace if analisi else (snap.pace if snap else 0)
    rate = analisi.rate if analisi else (snap.rate if snap else 0)
    trend = analisi.trend if analisi else "flat"

    # Confronto con ~7 giorni fa (dal nostro storico giornaliero).
    vecchio = storage.snapshot_di_circa_giorni_fa(pid, 7)
    ha_confronto = vecchio is not None
    delta = round(calc - vecchio.score, 2) if vecchio else 0.0
    delta_rec = (n_tot - vecchio.num_reviews) if vecchio else 0

    out = {
        "id": pid, "nome": nome, "hotel_id": hotel_id,
        "ha_dettaglio": analisi is not None,
        "calc": round(calc, 2), "n_totali": n_tot,
        "pace": round(pace, 2), "rate": rate, "trend": trend,
        "w7": list(analisi.w7) if (analisi and analisi.w7) else None,
        "w30": list(analisi.w30) if (analisi and analisi.w30) else None,
        "n3": analisi.n3 if analisi else None,
        "ha_confronto": ha_confronto, "delta": delta, "delta_recensioni": delta_rec,
        "storico_labels": analisi.storico_labels if analisi else [],
        "storico_valori": analisi.storico_valori if analisi else [],
        "proiezione_labels": analisi.proiezione_labels if analisi else [],
        "proiezione_valori": analisi.proiezione_valori if analisi else [],
        "gradini": analisi.gradini if analisi else [],
        "sottoreparti": analisi.sottoreparti if analisi else [],
    }
    return out


def costruisci_dati_dashboard(config: dict) -> dict:
    strutture_cfg = config.get("strutture", [])
    # Se non ho config, ricostruisco l'elenco dallo storico.
    if not strutture_cfg:
        visti = {}
        for s in storage.leggi_storico():
            visti[s.property_id] = {"id": s.property_id, "nome": s.property_name, "hotel_id": ""}
        strutture_cfg = list(visti.values())

    strutture = []
    for cfg in strutture_cfg:
        if "METTI" in str(cfg.get("hotel_id", "")):
            continue
        d = _dati_struttura(cfg)
        if d:
            strutture.append(d)

    prev = config.get("previsione", {})
    return {
        "generato_il": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "obiettivo": prev.get("voto_obiettivo"),
        "strutture": strutture,
    }


def genera_html(config: dict) -> Path:
    dati = costruisci_dati_dashboard(config)
    storage.DATA_DIR.mkdir(parents=True, exist_ok=True)
    html = _TEMPLATE.replace("/*DATI_JSON*/", json.dumps(dati, ensure_ascii=False))
    DASHBOARD_FILE.write_text(html, encoding="utf-8")
    return DASHBOARD_FILE


# ---------------------------------------------------------------------------
_TEMPLATE = r"""<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cruscotto Reputazione Booking</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
  :root{--ink:#241F1B;--muted:#6F665C;--cream:#FBF8F3;--line:#E6DECF;--petrol:#0F3A3E;
        --gold:#C2A14D;--goldsoft:#E9DCBB;--green:#2F6E54;--greenbg:#EEF4EF;
        --terra:#B05129;--terrabg:#F8EFE8}
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;
       color:var(--ink);background:var(--cream);line-height:1.5}
  header.top{background:var(--petrol);color:#fff;padding:20px 24px}
  header.top h1{font-size:21px;font-weight:800;letter-spacing:-.3px}
  header.top .sub{font-size:13px;color:var(--goldsoft);margin-top:4px}
  .wrap{max-width:1000px;margin:0 auto;padding:22px 16px 60px}
  .card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:20px;margin-bottom:20px}
  .nome{font-size:17px;font-weight:800;color:var(--petrol)}
  .sotto{font-size:12.5px;color:var(--muted);margin-top:2px}
  .voto-riga{display:flex;align-items:baseline;gap:12px;margin:12px 0}
  .voto{font-size:46px;font-weight:800;color:var(--petrol);line-height:1}
  .su10{color:var(--muted);font-size:14px}
  .delta{font-size:13px;font-weight:700;padding:3px 10px;border-radius:999px}
  .delta.su{background:var(--greenbg);color:var(--green)}
  .delta.giu{background:var(--terrabg);color:var(--terra)}
  .delta.pari{background:#eef2f6;color:var(--muted)}
  .grid{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));margin:14px 0}
  .kpi{background:var(--cream);border-radius:10px;padding:10px 12px}
  .kpi .l{font-size:10.5px;letter-spacing:.4px;text-transform:uppercase;color:var(--muted);font-weight:700}
  .kpi .v{font-size:22px;font-weight:800;color:var(--petrol);margin-top:2px}
  .kpi .n{font-size:11px;color:var(--muted)}
  .verdict{border-radius:12px;padding:14px 16px;margin:8px 0 4px;font-size:15px;font-weight:700}
  .verdict.up{background:var(--greenbg);color:var(--green);border-left:5px solid var(--green)}
  .verdict.down{background:var(--terrabg);color:var(--terra);border-left:5px solid var(--terra)}
  .verdict.flat{background:#eef2f6;color:var(--muted);border-left:5px solid var(--muted)}
  .steps{display:grid;gap:8px;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));margin:12px 0}
  .step{background:#fff;border:1px solid var(--line);border-top:4px solid var(--gold);
        border-radius:0 0 10px 10px;padding:10px 12px}
  .step .t{font-size:20px;font-weight:800;color:var(--petrol)}
  .step .when{font-size:12.5px;font-weight:700;margin-top:2px}
  .step .lbl{font-size:10px;color:var(--gold);font-weight:800;text-transform:uppercase;margin-top:3px}
  .chart-box{position:relative;height:260px;margin-top:10px}
  table.subs{width:100%;border-collapse:collapse;font-size:13px;margin-top:12px}
  table.subs th{text-align:left;background:var(--petrol);color:#fff;font-size:10.5px;
                text-transform:uppercase;padding:8px 9px;font-weight:700}
  table.subs th:not(:first-child),table.subs td:not(:first-child){text-align:center}
  table.subs td{padding:9px;border-bottom:1px solid var(--line)}
  table.subs .cat{font-weight:700;color:var(--petrol)}
  .tr-up{color:var(--green);font-weight:700}.tr-down{color:var(--terra);font-weight:700}
  .tr-flat{color:var(--muted);font-weight:700}
  .nota{font-size:12px;color:var(--muted);margin-top:22px;line-height:1.5}
  .vuoto{background:#fff;border:1px dashed var(--line);border-radius:14px;padding:40px;
         text-align:center;color:var(--muted)}
  details{margin-top:12px}summary{cursor:pointer;font-size:13px;color:var(--petrol);font-weight:700}
</style>
</head>
<body>
<header class="top">
  <h1>Cruscotto Reputazione Booking</h1>
  <div class="sub" id="sub"></div>
</header>
<div class="wrap" id="wrap"></div>

<script>
const DATI = /*DATI_JSON*/;
const wrap=document.getElementById("wrap");
document.getElementById("sub").textContent="Aggiornato il "+DATI.generato_il+
  " · "+DATI.strutture.length+" strutture";

function n2(x){return (x==null?"-":Number(x).toFixed(2).replace(".",","));}
function n1(x){return (x==null?"-":Number(x).toFixed(1).replace(".",","));}

if(!DATI.strutture.length){
  wrap.innerHTML='<div class="vuoto">Nessun dato ancora. Lancia <b>python3 run.py demo</b> '+
    'per una prova, oppure <b>python3 run.py giornaliero</b> con Booking collegato.</div>';
}

DATI.strutture.forEach((s,i)=>{
  const card=document.createElement("div");card.className="card";

  const cd=s.delta>0?"su":(s.delta<0?"giu":"pari");
  const fr=s.delta>0?"▲":(s.delta<0?"▼":"▪");
  const sg=s.delta>0?"+":"";
  const deltaTxt=s.ha_confronto?(fr+" "+sg+n2(s.delta)+" vs 7 gg fa"):"primo rilevamento";

  // Verdetto
  let vClass="flat",vTxt="";
  if(s.trend==="up"){vClass="up";
    vTxt="Al ritmo degli ultimi 3 mesi (<b>"+n2(s.pace)+"</b>) il voto <b>SALE</b> verso ~"+n1(s.pace)+".";}
  else if(s.trend==="down"){vClass="down";
    vTxt="Attenzione: al ritmo degli ultimi 3 mesi (<b>"+n2(s.pace)+"</b>) il voto <b>SCENDE</b> verso ~"+n1(s.pace)+".";}
  else{vClass="flat";vTxt="Al ritmo attuale il voto resta <b>stabile</b> attorno a "+n2(s.calc)+".";}

  // KPI
  const kpi=`
    <div class="grid">
      <div class="kpi"><div class="l">Voto calcolato</div><div class="v">${n2(s.calc)}</div></div>
      <div class="kpi"><div class="l">Ritmo 3 mesi</div><div class="v">${n2(s.pace)}</div><div class="n">${s.n3?s.n3+" recensioni":""}</div></div>
      <div class="kpi"><div class="l">Media 7 gg</div><div class="v">${s.w7?n2(s.w7[0]):"n/d"}</div><div class="n">${s.w7?s.w7[1]+" recensioni":""}</div></div>
      <div class="kpi"><div class="l">Media 30 gg</div><div class="v">${s.w30?n2(s.w30[0]):"n/d"}</div><div class="n">${s.w30?s.w30[1]+" recensioni":""}</div></div>
      <div class="kpi"><div class="l">Recensioni totali</div><div class="v">${s.n_totali}</div></div>
      <div class="kpi"><div class="l">Recensioni / mese</div><div class="v">${s.rate||"-"}</div></div>
    </div>`;

  // Gradini
  let stepsHtml="";
  if(s.gradini && s.gradini.length){
    stepsHtml='<div class="steps">'+s.gradini.map(g=>
      '<div class="step"><div class="lbl" style="color:var(--muted)">Booking mostra</div>'+
      '<div class="t">'+n1(g.target)+'</div>'+
      '<div class="when">'+(g.mesi?g.quando+" · tra ~"+g.mesi+" mesi":"oltre 2 anni")+'</div>'+
      (g.badge?'<div class="lbl">'+g.badge+'</div>':'')+'</div>').join("")+'</div>';
  }

  // Sottoreparti
  let subsHtml="";
  if(s.sottoreparti && s.sottoreparti.length){
    const righe=s.sottoreparti.map(c=>{
      let tr,cls;
      if(c.trend==="up"){tr="↑ sale verso ~"+n1(c.pace);cls="tr-up";}
      else if(c.trend==="down"){tr="↓ scende verso ~"+n1(c.pace);cls="tr-down";}
      else{tr="= stabile";cls="tr-flat";}
      const nx=c.prossimo?("<b>"+n1(c.prossimo)+"</b> · "+c.quando):"—";
      return "<tr><td class='cat'>"+c.label+"</td><td class='big'>"+n2(c.calc)+
        "</td><td>"+n2(c.pace)+"</td><td class='"+cls+"'>"+tr+"</td><td>"+nx+"</td></tr>";
    }).join("");
    subsHtml='<details><summary>Dettaglio sottoreparti (Pulizia, Personale, ...)</summary>'+
      '<table class="subs"><thead><tr><th>Categoria</th><th>Oggi</th><th>3 mesi</th>'+
      '<th>Tendenza</th><th>Prossimo gradino</th></tr></thead><tbody>'+righe+'</tbody></table></details>';
  }

  const chartHtml = s.ha_dettaglio
    ? '<div class="chart-box"><canvas id="ch'+i+'"></canvas></div>'
    : '<div class="nota">Dettaglio storico/proiezione non disponibile: manca il file recensioni scaricato per questa struttura.</div>';

  card.innerHTML=
    '<div class="nome">'+s.nome+'</div>'+
    '<div class="sotto">'+(s.hotel_id?"hotel_id "+s.hotel_id:"")+'</div>'+
    '<div class="voto-riga"><div class="voto">'+n1(s.calc)+'</div><div class="su10">/ 10</div>'+
      '<div class="delta '+cd+'">'+deltaTxt+'</div></div>'+
    '<div class="verdict '+vClass+'">'+vTxt+'</div>'+
    kpi+stepsHtml+chartHtml+subsHtml;
  wrap.appendChild(card);

  // Grafico storico + proiezione
  if(s.ha_dettaglio){
    const labels=s.storico_labels.concat(s.proiezione_labels);
    const nHist=s.storico_labels.length, nProj=s.proiezione_labels.length;
    const storico=s.storico_valori.concat(new Array(nProj).fill(null));
    // la proiezione parte dall'ultimo punto storico per collegare le linee
    const proj=new Array(Math.max(0,nHist-1)).fill(null)
      .concat([s.storico_valori[nHist-1]]).concat(s.proiezione_valori);
    const su=s.trend==="up";
    const ys=s.storico_valori.concat(s.proiezione_valori);
    const ymin=Math.floor((Math.min(...ys)-0.1)*10)/10, ymax=Math.ceil((Math.max(...ys)+0.1)*10)/10;
    new Chart(document.getElementById("ch"+i),{type:"line",
      data:{labels:labels,datasets:[
        {label:"Storico",data:storico,borderColor:"#0F6E56",borderWidth:2,pointRadius:0,tension:.25},
        {label:"Se continui come gli ultimi 3 mesi",data:proj,
         borderColor:su?"#2F6E54":"#B05129",borderDash:[7,3],borderWidth:2,pointRadius:0,tension:.25}
      ]},
      options:{responsive:true,maintainAspectRatio:false,
        plugins:{legend:{labels:{boxWidth:16,font:{size:11}}},
          tooltip:{callbacks:{label:c=>c.dataset.label+": "+(c.parsed.y==null?"-":n2(c.parsed.y))}}},
        scales:{y:{min:ymin,max:ymax,ticks:{stepSize:0.1,callback:v=>n1(v)}},
                x:{ticks:{autoSkip:true,maxRotation:45,font:{size:10}},grid:{display:false}}}}});
  }
});

if(DATI.strutture.length){
  const nota=document.createElement("div");nota.className="nota";
  nota.innerHTML="Modello: il voto calcolato pesa di piu' le recensioni recenti (peso dimezzato ogni 6 mesi), "+
    "come stima di cio' che Booking mostra. La proiezione ipotizza di mantenere il ritmo e la qualita' "+
    "degli ultimi 3 mesi ed e' un'indicazione, non una garanzia.";
  wrap.appendChild(nota);
}
</script>
</body>
</html>
"""
