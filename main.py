
import requests
import pandas as pd
import duckdb

def extract_energy_charts_data(country_code="it"):
    print(f"Downloading energy data for: {country_code.upper()}...")
    url = f"https://api.energy-charts.info/public_power?country={country_code}"
    
    # API Call
    response = requests.get(url)
    if response.status_code != 200:
        print("Error: Failed to download data from the API.")
        return None
        
    json_data = response.json()
    
    # Extract and convert timestamps
    timestamps = json_data['unix_seconds']
    utc_dates = pd.to_datetime(timestamps, unit='s', utc=True)
    local_dates = utc_dates.tz_convert('Europe/Rome')
    
    # Create DataFrame (We keep Datetime as a standard column for DuckDB)
    df = pd.DataFrame({'Datetime': local_dates})
    
    # Add columns dynamically
    for source in json_data['production_types']:
        source_name = source['name']
        values = source['data']
        df[source_name] = values
        
    return df

# --- Pipeline Execution ---
# 1. Extract
energy_df = extract_energy_charts_data("it")

if energy_df is not None:
    print("\nExtraction successful!")
    
    # 2. Load (Salvataggio nel Database DuckDB)
    print("Connecting to DuckDB...")
    
    # Crea un file fisico chiamato 'energy_project.duckdb' nel tuo computer
    conn = duckdb.connect('energy_project.duckdb')
    
    # DuckDB legge la variabile 'energy_df' automaticamente.
    # Usiamo "CREATE OR REPLACE TABLE" per aggiornare i dati se esegui lo script più volte
    conn.execute("CREATE OR REPLACE TABLE italy_power_production AS SELECT * FROM energy_df")
    
    # Chiudiamo la connessione
    conn.close()
    
    print("Load successful! Data saved into the DuckDB database 'energy_project.duckdb'.")
