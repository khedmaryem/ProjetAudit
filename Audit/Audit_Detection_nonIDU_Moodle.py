from bs4 import BeautifulSoup
import re
import json

# 1. Lire le fichier HTML
# Remplace 'ton_fichier.html' par le vrai chemin de ton fichier
chemin_fichier_html = r'Audit IDU\Audit IDU\Resume_Moodle_IDU.html'

try:
    with open(chemin_fichier_html, 'r', encoding='utf-8') as f:
        html_content = f.read()
except FileNotFoundError:
    print(f"Erreur : Le fichier {chemin_fichier_html} est introuvable.")
    exit()

# 2. Analyser le HTML avec BeautifulSoup
soup = BeautifulSoup(html_content, 'html.parser')

# 3. Trouver tous les blocs qui contiennent un cours entier
blocs_cours = soup.find_all('div', class_='coursebox')

anomalies = []
donnees_valides = []

# 4. Analyser chaque bloc de cours un par un
for bloc in blocs_cours:
    # --- Extraction du Nom du cours ---
    # On cherche la balise qui a la classe 'coursename'
    balise_nom = bloc.find(class_='coursename')
    nom_cours = balise_nom.get_text(strip=True) if balise_nom else "Nom du cours introuvable"
    
    # --- Extraction de la Catégorie ---
    # On cherche la balise div qui a la classe 'coursecat'
    balise_categorie = bloc.find('div', class_='coursecat')
    texte_categorie = balise_categorie.get_text(strip=True) if balise_categorie else "Aucune catégorie renseignée"
    
    # --- Vérification IDU3, IDU4 ou IDU5 ---
    # On cherche le motif dans le texte de la catégorie
    match_idu = re.search(r'(IDU[345]?)', texte_categorie)
    est_transversal = "Cours Transversaux" in texte_categorie
    
    if match_idu or est_transversal:
        if match_idu:
            niveau = match_idu.group(1)
        else:
            niveau = "Transversal"
            
        # C'est valide, on garde l'info de côté pour les statistiques
        # CORRECTION : on utilise bien la variable "niveau" ici !
        donnees_valides.append({
            "coursename": nom_cours,
            "categorie": texte_categorie,
            "niveau_detecte": niveau 
        })
    else:
        # Anomalie détectée ! On l'ajoute à notre liste d'erreurs
        anomalies.append({
            "coursename": nom_cours,
            "categorie": texte_categorie,
            "motif_erreur": "Absence de IDU3, IDU4 ou IDU5 dans la catégorie"
        })

# 5. Afficher un petit bilan dans la console
print(f"BILAN DE L'EXTRACTION :")
print(f"- Cours valides (avec IDU 3/4/5 ou Transversaux) : {len(donnees_valides)}")
print(f"- Anomalies détectées : {len(anomalies)}")

# 6. Exporter les anomalies dans un fichier JSON
chemin_export = r"C:\Semestre8\ProjetAudit\Data\Audit_Detection_nonIDU_Moodle.json"
with open(chemin_export, 'w', encoding='utf-8') as f:
    json.dump(anomalies, f, indent=4, ensure_ascii=False)

print(f"\nLes anomalies ont été sauvegardées dans le fichier : {chemin_export}")