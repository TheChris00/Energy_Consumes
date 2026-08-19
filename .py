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