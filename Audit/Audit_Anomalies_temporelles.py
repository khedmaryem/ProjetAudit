'''
La logique métier :

Anomalie mineure / suspecte : Un cours de moins de 45 minutes 
(généralement, le minimum syndical à l'université est de 1h ou 1h30).

Anomalie majeure / bloquante : Une séance (hors projet spécifique) qui dure plus 
de 4h30 d'affilée, ce qui dépasse la limite légale ou la capacité d'attention sans pause.'''

import pandas as pd
import re
import json
import re 

# Fonction pour garantir que la catégorie existera toujours meme si il n'y a aucune anomalie de ce type
def forcer_presence_categorie(df_filtre, nom_categorie):
    df = df_filtre.copy()
    if len(df) == 0:
        # Il n'y a aucune anomalie de ce type ! On crée une ligne fantôme avec des vides (None)
        return pd.DataFrame({
            'Title': [None],
            'Starts_FR': [pd.NaT],
            'Ends_FR': [pd.NaT],
            'Duree': [pd.NaT],
            'Type_Anomalie': [nom_categorie]
        })
    else:
        # Il y a des anomalies, on leur donne juste l'étiquette normale
        df['Type_Anomalie'] = nom_categorie
        return df
    
# Charger ADE
df_ade3 = pd.read_json(r'Audit IDU\Audit IDU\ADECal_IDU3.json')
df_ade4 = pd.read_json(r'Audit IDU\Audit IDU\ADECal_IDU4.json')
df_ade5 = pd.read_json(r'Audit IDU\Audit IDU\ADECal_IDU5.json')

# On fusionne tous les ADE en un seul DataFrame
df_ade = pd.concat([df_ade3, df_ade4, df_ade5], ignore_index=True)

# 1. Conversion sécurisée avec gestion des erreurs (errors='coerce')
# Si une date est invalide, Pandas mettra 'NaT' (Not a Time) au lieu de faire planter le script.
df_ade['Starts'] = pd.to_datetime(df_ade['Starts'], errors='coerce', utc=True)
df_ade['Ends'] = pd.to_datetime(df_ade['Ends'], errors='coerce', utc=True)

# --- BONUS AUDIT : Détecter les dates illisibles ---
# C'est une anomalie en soi ! On les compte et on les affiche.
dates_invalides = df_ade[df_ade['Starts'].isna() | df_ade['Ends'].isna()]
print(f" Nombre d'événements avec des dates illisibles/vides : {len(dates_invalides)}")

# On supprime temporairement ces lignes corrompues pour pouvoir faire nos calculs de durée sans erreur
df_ade_propre = df_ade.dropna(subset=['Starts', 'Ends']).copy()

# 2. Conversion vers le fuseau horaire français
df_ade_propre['Starts_FR'] = df_ade_propre['Starts'].dt.tz_convert('Europe/Paris')
df_ade_propre['Ends_FR'] = df_ade_propre['Ends'].dt.tz_convert('Europe/Paris')

# 3. Calcul de la durée de la séance
df_ade_propre['Duree'] = df_ade_propre['Ends_FR'] - df_ade_propre['Starts_FR']
df_ade_propre['Heure_Debut'] = df_ade_propre['Starts_FR'].dt.hour
df_ade_propre['Jour_Semaine'] = df_ade_propre['Starts_FR'].dt.weekday # Lundi=0, Dimanche=6

# --- DÉTECTION DES ANOMALIES ---
cours_tardifs = df_ade_propre[df_ade_propre['Heure_Debut'] >= 20]
cours_weekend = df_ade_propre[df_ade_propre['Jour_Semaine'] >= 5]
cours_trop_courts = df_ade_propre[df_ade_propre['Duree'] < pd.Timedelta(minutes=45)]
cours_trop_longs = df_ade_propre[df_ade_propre['Duree'] > pd.Timedelta(hours=4, minutes=30)]

print("--- RÉSULTATS DE L'AUDIT ---")
print(f"Cours tardifs (>= 20h) : {len(cours_tardifs)}")
print(f"Cours le week-end : {len(cours_weekend)}")
print(f"Cours trop courts (< 45m) : {len(cours_trop_courts)}")
print(f"Cours trop longs (> 4h30) : {len(cours_trop_longs)}")

#-- TRAVAIL POUR FACILITER L UTILISATION DE POWER BI --
# Ajouter une étiquette pour identifier l'anomalie 

cours_tardifs = cours_tardifs.copy()
cours_tardifs['Type_Anomalie'] = 'Cours tardif (>= 20h00)'

cours_weekend = cours_weekend.copy()
cours_weekend['Type_Anomalie'] = 'Cours le week-end (Dimanche)'

cours_trop_courts = cours_trop_courts.copy()
cours_trop_courts['Type_Anomalie'] = 'Cours trop court (< 45m)'

cours_trop_longs = cours_trop_longs.copy()
cours_trop_longs['Type_Anomalie'] = 'Cours trop long (> 4h30)'

cours_tardifs = forcer_presence_categorie(cours_tardifs, 'Cours tardif (>= 20h)')
cours_weekend = forcer_presence_categorie(cours_weekend, 'Cours le week-end')
cours_trop_courts = forcer_presence_categorie(cours_trop_courts, 'Cours trop court (< 45m)')
cours_trop_longs = forcer_presence_categorie(cours_trop_longs, 'Cours trop long (> 4h30)')
#  Fusionner toutes les anomalies en un seul tableau
toutes_anomalies = pd.concat([cours_tardifs, cours_weekend, cours_trop_courts, cours_trop_longs], ignore_index=True)

# Préparer les données pour le JSON 
colonnes_export = ['Title', 'Starts_FR', 'Ends_FR', 'Duree', 'Type_Anomalie']
df_export = toutes_anomalies[colonnes_export].copy()

df_export['Starts_FR'] = pd.to_datetime(df_export['Starts_FR'], errors='coerce')
df_export['Ends_FR'] = pd.to_datetime(df_export['Ends_FR'], errors='coerce')

# Convertir les dates avec fuseau horaire en texte simple (format standard ISO)
df_export['Starts_FR'] = df_export['Starts_FR'].dt.strftime('%Y-%m-%d %H:%M:%S')
df_export['Ends_FR'] = df_export['Ends_FR'].dt.strftime('%Y-%m-%d %H:%M:%S')

# Convertir la durée (objet Timedelta) en minutes (nombre entier), beaucoup plus facile à filtrer/graphiquer dans Power BI
df_export['Duree'] = pd.to_timedelta(df_export['Duree'], errors='coerce')

df_export['Duree_minutes'] = (df_export['Duree'].dt.total_seconds() / 60).astype('Int64')

# On ajoute aussi une version texte de la durée pour l'affichage brut (ex: "05:00:00")
df_export['Duree_texte'] = df_export['Duree'].astype(str).str.split(' ').str[-1]

# On supprime la colonne 'Duree' d'origine car l'objet Timedelta fait planter l'export JSON
df_export = df_export.drop(columns=['Duree'])

# Exporter vers un fichier JSON
nom_fichier_json = r"C:\Semestre8\ProjetAudit\Data\Audit_Anomalies_temporelles.json"
df_export.to_json(nom_fichier_json, orient='records', force_ascii=False, indent=4)
print(f"Audit terminé ! Les anomalies temporelles ont été exportées dans le fichier : {nom_fichier_json}")