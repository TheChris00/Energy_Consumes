import duckdb
import pandas as pd

# Impostiamo Pandas per stampare la tabella in modo largo e pulito
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

print("Connessione al database DuckDB in corso...")

# 1. Apriamo il file del database
conn = duckdb.connect('energy_project.duckdb')

# 2. Scriviamo la query SQL
# Prendiamo le date più recenti e confrontiamo Rinnovabili vs Fossili
query = """
    SELECT 
        Datetime, 
        Solar, 
        "Wind onshore" AS Wind,
        "Fossil gas" AS Gas
    FROM italy_power_production 
    ORDER BY Datetime DESC
    LIMIT 15
"""

# 3. Eseguiamo la query e la trasformiamo in DataFrame
df_risultati = conn.execute(query).df()

print("\n--- ULTIMI 15 RECORD ENERGETICI (in Megawatt) ---")
print(df_risultati)

# 4. Chiudiamo la connessione
conn.close()
