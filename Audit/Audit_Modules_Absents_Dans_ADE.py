# Repondre a la question : Des modules ont-ils 0 séance planifiée malgré des heures prévues ?
import pandas as pd
import re
import json
import re 

def extraire_racine(code):
    """
    Cherche un code type 'INFO931' ou 'MATH101' dans le texte,
    en ignorant les préfixes (TP, TD, CM).
    """
    if pd.isna(code): return None
    # On cherche un bloc de lettres suivies de chiffres (ex: INFO931)
    match = re.search(r'([A-Z]{2,}\d{2,})', str(code))
    if match:
        return match.group(1)
    # Fallback : si on ne trouve pas le pattern, on prend le premier mot
    match = re.search(r'([A-Z0-9]+)', str(code))
    return match.group(1) if match else str(code)

def extraire_niveau(description):
    if pd.isna(description):
        return None
    match = re.search(r'IDU-(\d)', description)
    return match.group(1) if match else None


# Charger ADE
df_ade3 = pd.read_json(r'Audit IDU\Audit IDU\ADECal_IDU3.json')
df_ade4 = pd.read_json(r'Audit IDU\Audit IDU\ADECal_IDU4.json')
df_ade5 = pd.read_json(r'Audit IDU\Audit IDU\ADECal_IDU5.json')

# On fusionne tous les ADE en un seul DataFrame
df_ade = pd.concat([df_ade3, df_ade4, df_ade5], ignore_index=True)

# 2. Extractions rapides et propres sur ADE
df_ade['racine'] = df_ade['Title'].apply(extraire_racine)
# On extrait directement le chiffre après "IDU-" (ex: IDU-3 devient '3')
df_ade['niveau'] = df_ade['Description'].str.extract(r'IDU-(\d)')

# 3. Charger la Maquette
with open(r'Audit IDU\Audit IDU\MAQUETTE_IDU.json', 'r', encoding='utf-8') as f:
    data_maquette = json.load(f)

lignes_maquette = [] 
for item in data_maquette:
    if item.get("type") == "table" and item.get("name") == "MAQUETTE_module":
        lignes_maquette = item.get("data", []) 
        break

df_maquette = pd.DataFrame(lignes_maquette)
df_maquette['racine'] = df_maquette['code_module'].apply(extraire_racine)

# Niveau par module
# 4. Associer le "niveau" à chaque module de la maquette (basé sur ce qu'on a lu dans ADE)
niveau_par_module = (
    df_ade.groupby('racine')['niveau']
    .agg(lambda x: x.mode()[0] if not x.mode().empty else None)
    .reset_index()
)
niveau_par_module = niveau_par_module.dropna()

# Fusion propre : chaque module de la maquette reçoit son niveau (3, 4 ou 5)
df_maquette = pd.merge(df_maquette, niveau_par_module, on='racine', how='left')

# 5. Compter les séances ADE par racine et par niveau
bilan_ade = df_ade.groupby(['racine', 'niveau']).size().reset_index(name='nb_seances_planifiees')

# 6. Calcul des heures théoriques (MAQUETTE)
df_maquette['cm'] = pd.to_numeric(df_maquette['cm'], errors='coerce').fillna(0)
df_maquette['td'] = pd.to_numeric(df_maquette['td'], errors='coerce').fillna(0)
df_maquette['tp'] = pd.to_numeric(df_maquette['tp'], errors='coerce').fillna(0)
df_maquette['heures_prevues'] = df_maquette['cm'] + df_maquette['td'] + df_maquette['tp']

# 7. FUSION des deux mondes
resultat = pd.merge(
    df_maquette[['racine', 'code_module', 'nom', 'heures_prevues', 'niveau']],
    bilan_ade,
    on=['racine', 'niveau'],
    how='left'
)

# On remplace les NaN (ceux qui n'ont aucune séance) par 0
resultat['nb_seances_planifiees'] = resultat['nb_seances_planifiees'].fillna(0)

# 8. IDENTIFICATION DES ANOMALIES
resultat['alerte_manquante'] = (resultat['heures_prevues'] > 0) & (resultat['nb_seances_planifiees'] == 0)

#  Modules SANS NIVEAU (null) avec ALERTE (Ce que tu as demandé)
# Ces modules sont dans la maquette mais totalement absents d'ADE
niveau_inconnues = resultat[resultat['niveau'].isna() & (resultat['alerte_manquante'] == True)]

print(f"\n" + "="*50)
print(f"RAPPORT D'ANOMALIES")
print(f"="*50)

print(f"\nMODULES SANS NIVEAU DÉTERMINÉ (Absents d'ADE) :")
if not niveau_inconnues.empty:
    print("Attention : Ces modules sont dans la Maquette mais n'existent pas dans vos fichiers ADE.")
    print(niveau_inconnues[['racine', 'code_module', 'nom', 'heures_prevues']])
else:
    print("Aucun module orphelin (sans niveau) détecté.")

# 9. EXPORT
nom_fichier_json = r"C:\Semestre8\ProjetAudit\Data\Audit_Modules_Absents_Dans_ADE.json"
resultat.to_json(nom_fichier_json, orient='records', force_ascii=False)