"""Query di esplorazione e analisi sul database prodotto da main.py."""

import pandas as pd

from main import TABLE_NAME, get_connection

# Impostiamo Pandas per stampare la tabella in modo largo e pulito
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 2000)

# 1. Apriamo il database (lo stesso usato dalla pipeline: MotherDuck o locale)
conn = get_connection()

print("Exploring the database...\n")

try:
    # 1. THE COLUMN LIST (The Schema)
    # DESCRIBE asks the database how the table is structured
    schema = conn.execute(f"DESCRIBE {TABLE_NAME}").df()

    print("📋 LIST OF ALL AVAILABLE COLUMNS:")
    print("-" * 100)
    # Show only the column name and its data type (e.g., TIMESTAMP or DOUBLE)
    print(schema[["column_name", "column_type"]])
    print("-" * 100)

    # 2. FULL DATA PREVIEW
    # The asterisk (*) in SQL means "select all columns"
    query_all = f"""
        SELECT *
        FROM {TABLE_NAME}
        ORDER BY "Datetime" DESC
        LIMIT 3
    """

    full_data = conn.execute(query_all).df()

    print("\n🔍 DATA PREVIEW (Last 3 rows with all energy sources):")
    print(full_data)

    print("\n🌿 ANALISI SOSTENIBILITÀ AVVIATA...\n")

    # --- DOMANDA 1 & 2: Qual è la % rinnovabile e in quali ore la rete è più "pulita"? ---
    # Raggruppiamo i dati per ora del giorno e calcoliamo la percentuale media di rinnovabili
    query_ore_pulite = f"""
        SELECT
            EXTRACT(HOUR FROM "Datetime") AS Ora_del_Giorno,
            ROUND(AVG("Renewable share of generation"), 1) AS Perc_Rinnovabile_Media,
            ROUND(AVG("Solar"), 0) AS Produzione_Solare_MW,
            ROUND(AVG("Fossil gas"), 0) AS Produzione_Gas_MW
        FROM {TABLE_NAME}
        WHERE "Datetime" IS NOT NULL
        GROUP BY Ora_del_Giorno
        ORDER BY Perc_Rinnovabile_Media DESC
        LIMIT 5
    """

    # --- DOMANDA 3: Il fotovoltaico vs la domanda totale (Load) ---
    # Guardiamo le ore centrali della giornata per vedere se il sole copre il picco di consumi
    query_sole_vs_condizionatori = f"""
        SELECT
            EXTRACT(HOUR FROM "Datetime") AS Ora,
            ROUND(AVG("Load"), 0) AS Domanda_Totale_MW,
            ROUND(AVG("Solar"), 0) AS Copertura_Solare_MW,
            ROUND((AVG("Solar") / NULLIF(AVG("Load"), 0)) * 100, 1) AS Perc_Coperta_Dal_Sole
        FROM {TABLE_NAME}
        WHERE EXTRACT(HOUR FROM "Datetime") BETWEEN 10 AND 16
        GROUP BY Ora
        ORDER BY Ora ASC
    """

    print("🏆 LE 5 ORE PIÙ 'PULITE' DELLA GIORNATA:")
    print("-" * 70)
    print(conn.execute(query_ore_pulite).df())
    print("-" * 70)

    print("\n☀️ IL SOLE RIESCE A COPRIRE I CONSUMI DIURNI?")
    print("-" * 70)
    print(conn.execute(query_sole_vs_condizionatori).df())
    print("-" * 70)
finally:
    conn.close()
