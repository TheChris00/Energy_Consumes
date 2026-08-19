
import requests
import pandas as pd
import duckdb
import os
from dotenv import load_dotenv

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
    conn = duckdb.connect('md:my_db?motherduck_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6ImNocmlzdGlhbmdyYXNzbzY1QGdtYWlsLmNvbSIsIm1kUmVnaW9uIjoiYXdzLWV1LWNlbnRyYWwtMSIsInNlc3Npb24iOiJjaHJpc3RpYW5ncmFzc282NS5nbWFpbC5jb20iLCJwYXQiOiI3NVYxOENvd0ZRcWhmRENlRTVTSjN4MnRfQVNXZVpXSDFDQWpYWUhjOFBJIiwidXNlcklkIjoiYmRmYTY1ZGEtMjdlZi00NTZlLWE5NWItMTE5NDdjNGUzYzkyIiwiaXNzIjoibWRfcGF0IiwicmVhZE9ubHkiOmZhbHNlLCJ0b2tlblR5cGUiOiJyZWFkX3dyaXRlIiwiaWF0IjoxNzg3MTU5NDA3fQ.FKYwNEV4kj0hsysGJFDz688j0ZGiUHaVRTaqxGSm2WU')
    
    # DuckDB legge la variabile 'energy_df' automaticamente.
    # Usiamo "CREATE OR REPLACE TABLE" per aggiornare i dati se esegui lo script più volte
    conn.execute("CREATE OR REPLACE TABLE italy_power_production AS SELECT * FROM energy_df")
    
    # Chiudiamo la connessione
    conn.close()
    
    print("Load successful! Data saved into the DuckDB database 'energy_project.duckdb'.")


# Apri la cassaforte virtuale
load_dotenv()

# Prendi il token segreto
token = os.getenv("MOTHERDUCK_TOKEN")

# Connettiti a MotherDuck usando il token appena letto
conn = duckdb.connect(f'md:my_db?motherduck_token={token}')