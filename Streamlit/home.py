"""Dashboard sulla rete elettrica italiana.

Tre domande, tre tab. Il SQL sta in db.py, qui c'e' solo il layout.
Avvio:  streamlit run Streamlit/home.py
"""

import streamlit as st

import db

st.set_page_config(page_title="Rete elettrica italiana", page_icon="⚡", layout="wide")

st.title("⚡ La rete elettrica italiana, in tempo reale")

# --- Filtro globale: uno solo, nella sidebar ---
PERIODI = {"Ultime 24 ore": 1, "Ultimi 7 giorni": 7, "Ultimi 30 giorni": 30, "Tutto": 3650}
scelta = st.sidebar.selectbox("Periodo", list(PERIODI))
giorni = PERIODI[scelta]

copertura = db.copertura_dati()
st.sidebar.caption(
    f"{copertura.righe:,} rilevazioni\n\n"
    f"da {copertura.inizio:%d/%m/%Y} a {copertura.fine:%d/%m/%Y %H:%M}"
)

# --- I 4 numeri in cima: lo stato della rete a colpo d'occhio ---
stato = db.stato_attuale()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Quota rinnovabile", f"{stato.perc_rinnovabile:.0f}%")
c2.metric("Domanda", f"{stato.domanda_mw:,.0f} MW")
c3.metric(
    "Saldo con l'estero",
    f"{abs(stato.saldo_estero_mw):,.0f} MW",
    "importiamo" if stato.saldo_estero_mw > 0 else "esportiamo",
    delta_color="off",
)
c4.metric("Ultimo dato", f"{stato.aggiornamento:%H:%M}", f"{stato.aggiornamento:%d/%m}",
          delta_color="off")

tab_green, tab_consumi, tab_estero = st.tabs(
    ["🌿 Sostenibilità", "📈 Consumi", "🌍 Import-Export"]
)

# =========================== SOSTENIBILITÀ ===========================
with tab_green:
    mix = db.mix_nel_tempo(giorni)
    rinn_media = mix.Rinnovabili.sum() / (mix.Rinnovabili.sum() + mix.Fossili.sum()) * 100
    st.subheader(f"Nel periodo il {rinn_media:.0f}% della produzione è stata rinnovabile")
    st.area_chart(mix.set_index("Datetime"), color=["#e07b39", "#7cb342", "#5b8fc9"])
    st.caption(
        "Rinnovabili = solare, eolico, idroelettrico, biomasse, geotermico. "
        "L'import è l'energia comprata dall'estero."
    )

    col_sx, col_dx = st.columns(2)

    with col_sx:
        ore = db.rinnovabile_per_ora(giorni)
        migliore = ore.loc[ore.Perc_Rinnovabile.idxmax()]
        st.subheader(f"La rete è più pulita verso le {migliore.Ora:.0f}:00")
        st.bar_chart(ore.set_index("Ora"), color="#7cb342")
        st.caption(
            f"Alle {migliore.Ora:.0f}:00 la quota rinnovabile tocca il "
            f"{migliore.Perc_Rinnovabile:.0f}%: è l'ora giusta per lavatrice e ricarica auto."
        )

    with col_dx:
        sole = db.sole_vs_domanda(giorni)
        diurno = sole[sole.Ora.between(10, 16)]
        picco = diurno.loc[diurno.Perc_Coperta.idxmax()] if not diurno.empty else None
        titolo = (
            f"A mezzogiorno il sole copre il {picco.Perc_Coperta:.0f}% dei consumi"
            if picco is not None else "Il fotovoltaico contro la domanda"
        )
        st.subheader(titolo)
        st.line_chart(sole.set_index("Ora")[["Domanda", "Solare"]],
                      color=["#c9503b", "#f2b705"])
        st.caption("Quanto del fabbisogno regge il fotovoltaico nelle ore dei condizionatori.")

# =============================== CONSUMI ===============================
with tab_consumi:
    carico = db.carico_feriali_weekend(giorni)
    pivot = carico.pivot(index="Ora", columns="Tipo", values="Domanda")

    punta = carico.loc[carico.Domanda.idxmax()]
    st.subheader(f"Il picco di consumo è alle {punta.Ora:.0f}:00")
    st.line_chart(pivot, color=["#c9503b", "#5b8fc9"][: pivot.shape[1]])

    if "Weekend" not in pivot.columns:
        st.info(
            "Non ci sono ancora dati di weekend nel periodo scelto: "
            "il confronto feriali/weekend compare quando la pipeline avrà più storico."
        )
    else:
        scarto = (1 - pivot.Weekend.mean() / pivot.Feriali.mean()) * 100
        st.caption(f"Nel weekend l'Italia consuma in media il {scarto:.0f}% in meno.")

# ============================ IMPORT-EXPORT ============================
with tab_estero:
    st.subheader("Quanta energia compriamo dall'estero")
    saldo = db.saldo_estero(giorni)
    st.area_chart(saldo.set_index("Datetime"), color="#5b8fc9")
    st.caption("Valori positivi = importiamo, negativi = esportiamo.")

    notte = db.mix_notturno(giorni).iloc[0]
    st.subheader("Di notte, quando il solare è a zero, l'Italia si accende così")
    st.bar_chart(notte, horizontal=True, color="#8e7cc3")
    st.caption(
        f"Media nelle ore senza sole: {notte.Gas:,.0f} MW dal gas e "
        f"{notte.Import:,.0f} MW importati. È qui che si vede quanto la transizione "
        "dipenda ancora dagli accumuli."
    )
