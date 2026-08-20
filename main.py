"""Pipeline ETL: energy-charts.info -> DuckDB (locale o MotherDuck)."""

import os

import duckdb
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.energy-charts.info/public_power"
TABLE_NAME = "italy_power_production"
LOCAL_DB = "energy_project.duckdb"
REQUEST_TIMEOUT = 30


def get_connection():
    """Apre MotherDuck se il token e' disponibile, altrimenti il file locale."""
    token = os.getenv("MOTHERDUCK_TOKEN")
    if token:
        print("Connecting to MotherDuck (md:my_db)...")
        return duckdb.connect(f"md:my_db?motherduck_token={token}")

    print(f"MOTHERDUCK_TOKEN not set: using the local database '{LOCAL_DB}'.")
    return duckdb.connect(LOCAL_DB)


def extract_energy_charts_data(country_code="it"):
    print(f"Downloading energy data for: {country_code.upper()}...")

    # API Call
    response = requests.get(
        API_URL, params={"country": country_code}, timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()

    json_data = response.json()

    # Extract and convert timestamps
    timestamps = json_data["unix_seconds"]
    utc_dates = pd.to_datetime(timestamps, unit="s", utc=True)
    local_dates = utc_dates.tz_convert("Europe/Rome")

    # Create DataFrame (We keep Datetime as a standard column for DuckDB)
    df = pd.DataFrame({"Datetime": local_dates})

    # Add columns dynamically
    for source in json_data["production_types"]:
        source_name = source["name"]
        values = source["data"]
        if len(values) != len(df):
            raise ValueError(
                f"Series '{source_name}' has {len(values)} values "
                f"but there are {len(df)} timestamps."
            )
        df[source_name] = values

    return df


def load_to_duckdb(conn, df):
    """Aggiunge i dati nuovi senza cancellare lo storico gia' salvato."""
    conn.register("energy_df", df)

    # Prima esecuzione: crea la tabella vuota con lo schema del DataFrame
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLE_NAME} AS "
        "SELECT * FROM energy_df WHERE FALSE"
    )

    # Se l'API aggiunge una nuova fonte di produzione, allarga la tabella
    existing = {
        row[0] for row in conn.execute(f"DESCRIBE {TABLE_NAME}").fetchall()
    }
    for column in df.columns:
        if column not in existing:
            print(f"New column detected: '{column}' - adding it to the table.")
            conn.execute(
                f'ALTER TABLE {TABLE_NAME} ADD COLUMN "{column}" DOUBLE'
            )

    columns = ", ".join(f'"{column}"' for column in df.columns)

    # Upsert: i timestamp gia' presenti vengono riscritti (l'API rivede i dati
    # piu' recenti), tutto il resto dello storico resta intatto.
    conn.execute(
        f'DELETE FROM {TABLE_NAME} '
        f'WHERE "Datetime" IN (SELECT "Datetime" FROM energy_df)'
    )
    conn.execute(
        f"INSERT INTO {TABLE_NAME} ({columns}) SELECT {columns} FROM energy_df"
    )

    total = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
    print(f"Load successful! {len(df)} rows written, {total} rows in total.")


def main():
    # 1. Extract
    energy_df = extract_energy_charts_data("it")
    print(f"\nExtraction successful! {len(energy_df)} rows downloaded.")

    # 2. Load
    conn = get_connection()
    try:
        load_to_duckdb(conn, energy_df)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
