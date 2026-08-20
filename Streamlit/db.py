"""Accesso ai dati per la dashboard: connessione + query, tutto cachato.

Regola: qui dentro sta il SQL, in home.py sta solo il layout.
L'aggregazione la fa DuckDB, non pandas.
"""

import os
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

TABLE = "italy_power_production"
LOCAL_DB = ROOT / "energy_project.duckdb"

# Le 22 colonne dell'API raggruppate in 3 famiglie leggibili.
RINNOVABILI = [
    "Solar", "Wind onshore", "Wind offshore", "Hydro Run-of-River",
    "Hydro water reservoir", "Biomass", "Geothermal",
]
FOSSILI = [
    "Fossil gas", "Fossil hard coal", "Fossil oil", "Fossil coal-derived gas",
]


def _somma(colonne):
    """SUM di piu' colonne trattando i NULL come zero."""
    return " + ".join(f'COALESCE("{c}", 0)' for c in colonne)


@st.cache_resource
def get_conn():
    """Una sola connessione per tutta la sessione (non ad ogni click)."""
    token = os.getenv("MOTHERDUCK_TOKEN")
    if token:
        return duckdb.connect(f"md:my_db?motherduck_token={token}")
    return duckdb.connect(str(LOCAL_DB), read_only=True)


def _query(sql, params=None):
    return get_conn().execute(sql, params or []).df()


@st.cache_data(ttl=1800)  # 30 min: stesso ritmo del job di ingestion
def stato_attuale():
    """I 4 numeri in cima alla pagina: l'ultima riga disponibile."""
    return _query(f'''
        SELECT
            "Datetime"                            AS aggiornamento,
            "Renewable share of generation"       AS perc_rinnovabile,
            "Load"                                AS domanda_mw,
            "Cross border electricity trading"    AS saldo_estero_mw
        FROM {TABLE}
        ORDER BY "Datetime" DESC
        LIMIT 1
    ''').iloc[0]


@st.cache_data(ttl=1800)
def copertura_dati():
    """Da quando a quando abbiamo dati (serve per avvisare se manca storico)."""
    return _query(f'''
        SELECT MIN("Datetime") AS inizio,
               MAX("Datetime") AS fine,
               COUNT(*)        AS righe
        FROM {TABLE}
    ''').iloc[0]


@st.cache_data(ttl=1800)
def mix_nel_tempo(giorni):
    """Rinnovabili vs fossili vs import, per l'area chart impilato."""
    return _query(f'''
        SELECT
            "Datetime"                                        AS Datetime,
            {_somma(RINNOVABILI)}                             AS Rinnovabili,
            {_somma(FOSSILI)}                                 AS Fossili,
            GREATEST(COALESCE("Cross border electricity trading", 0), 0) AS Import
        FROM {TABLE}
        WHERE "Datetime" >= now() - INTERVAL ($1) DAY
        ORDER BY "Datetime"
    ''', [giorni])


@st.cache_data(ttl=1800)
def rinnovabile_per_ora(giorni):
    """In quali ore la rete e' piu' pulita."""
    return _query(f'''
        SELECT
            EXTRACT(HOUR FROM "Datetime")                       AS Ora,
            ROUND(AVG("Renewable share of generation"), 1)      AS Perc_Rinnovabile
        FROM {TABLE}
        WHERE "Datetime" >= now() - INTERVAL ($1) DAY
        GROUP BY Ora
        ORDER BY Ora
    ''', [giorni])


@st.cache_data(ttl=1800)
def sole_vs_domanda(giorni):
    """Il fotovoltaico regge il picco diurno dei consumi?"""
    return _query(f'''
        SELECT
            EXTRACT(HOUR FROM "Datetime")   AS Ora,
            ROUND(AVG("Load"), 0)           AS Domanda,
            ROUND(AVG("Solar"), 0)          AS Solare,
            ROUND(AVG("Solar") / NULLIF(AVG("Load"), 0) * 100, 1) AS Perc_Coperta
        FROM {TABLE}
        WHERE "Datetime" >= now() - INTERVAL ($1) DAY
        GROUP BY Ora
        ORDER BY Ora
    ''', [giorni])


@st.cache_data(ttl=1800)
def carico_feriali_weekend(giorni):
    """Curva di carico media: giorni lavorativi contro weekend."""
    return _query(f'''
        SELECT
            EXTRACT(HOUR FROM "Datetime") AS Ora,
            CASE WHEN EXTRACT(DOW FROM "Datetime") IN (0, 6)
                 THEN 'Weekend' ELSE 'Feriali' END AS Tipo,
            ROUND(AVG("Load"), 0) AS Domanda
        FROM {TABLE}
        WHERE "Datetime" >= now() - INTERVAL ($1) DAY
        GROUP BY Ora, Tipo
        ORDER BY Ora
    ''', [giorni])


@st.cache_data(ttl=1800)
def mix_notturno(giorni):
    """Con cosa accendiamo l'Italia quando il sole e' a zero."""
    return _query(f'''
        SELECT
            ROUND(AVG(COALESCE("Fossil gas", 0)), 0)          AS "Gas",
            ROUND(AVG({_somma(RINNOVABILI)}), 0)              AS "Rinnovabili",
            ROUND(AVG(GREATEST(COALESCE("Cross border electricity trading", 0), 0)), 0) AS "Import",
            ROUND(AVG(COALESCE("Hydro pumped storage", 0)), 0) AS "Pompaggio"
        FROM {TABLE}
        WHERE "Datetime" >= now() - INTERVAL ($1) DAY
          AND COALESCE("Solar", 0) = 0
    ''', [giorni])


@st.cache_data(ttl=1800)
def saldo_estero(giorni):
    """Import (positivo) ed export (negativo) nel tempo."""
    return _query(f'''
        SELECT "Datetime" AS Datetime,
               "Cross border electricity trading" AS Saldo_MW
        FROM {TABLE}
        WHERE "Datetime" >= now() - INTERVAL ($1) DAY
        ORDER BY "Datetime"
    ''', [giorni])
