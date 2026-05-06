#Repondre a la question: Est ce que tout les modules qui sont dans maquette sont sur Moodle ??

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

# Charger ADE
df_ade3 = pd.read_json(r'Audit IDU\Audit IDU\ADECal_IDU3.json')
df_ade4 = pd.read_json(r'Audit IDU\Audit IDU\ADECal_IDU4.json')
df_ade5 = pd.read_json(r'Audit IDU\Audit IDU\ADECal_IDU5.json')
df_ade = pd.concat([df_ade3, df_ade4, df_ade5], ignore_index=True)

with open(r'Tous_Les_Cours_Moodle.json', 'r', encoding='utf-8') as f:
    data_moodle = json.load(f)

df_moodle = pd.DataFrame(data_moodle)

with open(r'Audit IDU\Audit IDU\MAQUETTE_IDU.json', 'r', encoding='utf-8') as f:
    data_maquette = json.load(f)

lignes_maquette = [] 
for item in data_maquette:
    if item.get("type") == "table" and item.get("name") == "MAQUETTE_module":
        lignes_maquette = item.get("data", []) 
        break
df_maquette = pd.DataFrame(lignes_maquette)

df_maquette['racine'] = df_maquette['code_module'].apply(extraire_racine)
df_moodle['racine'] = df_moodle['coursename'].apply(extraire_racine)
df_ade['racine'] = df_ade['Title'].apply(extraire_racine)
df_ade = df_ade.dropna(subset=['racine']).drop_duplicates(subset=['racine'])

# 3. LA COMPARAISON (Le Croisement)
modules_manquants = df_maquette[~df_maquette['racine'].isin(df_moodle['racine'])]
modules_absents_ade = df_maquette[~df_maquette['racine'].isin(df_ade['racine'])]
print("\n" + "="*60)
print(" RÉSULTAT DU CROISEMENT : MAQUETTE vs MOODLE")
print("="*60)

print(f"Nombre de modules dans la maquette : {len(df_maquette)}")
print(f"Nombre de cours uniques trouvés sur Moodle : {len(df_moodle)}")
print(f"\nMODULES DANS MAQUETTE MAIS ABSENTS DE MOODLE : {len(modules_manquants)}")

if not modules_manquants.empty:
    # On affiche les infos utiles
    print(modules_manquants[['racine', 'code_module', 'nom']].to_string(index=False))
    nom_fichier_json = r"C:\Semestre8\ProjetAudit\Data\Modules_Maquette_PasMoodle.json"
    # Export en JSON pour Power BI
    modules_manquants.to_json(nom_fichier_json, orient='records', force_ascii=False)
    print("\nLe détail des modules manquants a été exporté dans 'Modules_Maquette_PasMoodle.json'")
else:
    print("\nFélicitations ! Tous les modules de la maquette ont été trouvés sur Moodle.")

print("\n" + "="*60)
print(" COMPARAISON MAQUETTE vs ADE")
print("="*60)

print(f"Modules dans la maquette : {len(df_maquette)}")
print(f"Modules trouvés dans ADE : {len(df_ade)}")
print(f"\nMODULES DE LA MAQUETTE ABSENTS DANS ADE : {len(modules_absents_ade)}")

if not modules_absents_ade.empty:
    print(modules_absents_ade[['racine', 'code_module', 'nom']].to_string(index=False))
    nom_fichier_json = r"C:\Semestre8\ProjetAudit\Data\Modules_Maquette_Pas_ADE.json"
    modules_absents_ade.to_json(
        nom_fichier_json,
        orient='records',
        force_ascii=False
    )

    print("\nExport effectué : Modules_Maquette_Pas_ADE.json")
else:
    print("\nTous les modules de la maquette sont présents dans ADE ")