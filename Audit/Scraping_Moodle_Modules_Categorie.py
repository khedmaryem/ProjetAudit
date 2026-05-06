from bs4 import BeautifulSoup
import re
import json

# 1. Lire le fichier HTML
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


tous_les_cours = []
nb_valides = 0
nb_anomalies = 0

# 4. Analyser chaque bloc de cours un par un
for bloc in blocs_cours:
    # --- Extraction du Nom du cours ---
    balise_nom = bloc.find(class_='coursename')
    nom_cours = balise_nom.get_text(strip=True) if balise_nom else "Nom du cours introuvable"
    
    # --- Extraction de la Catégorie ---
    balise_categorie = bloc.find('div', class_='coursecat')
    texte_categorie = balise_categorie.get_text(strip=True) if balise_categorie else "Aucune catégorie renseignée"
    
    # --- Vérification IDU ou Transversal ---
    match_idu = re.search(r'(IDU[345]?)', texte_categorie)
    est_transversal = "Cours Transversaux" in texte_categorie
    
    if match_idu or est_transversal:
        niveau = match_idu.group(1) if match_idu else "Transversal"
        motif = ""
        nb_valides += 1
    else:
        niveau = None
        nb_anomalies += 1
        
    # On ajoute LE COURS (qu'il soit bon ou mauvais) dans la liste globale
    tous_les_cours.append({
        "coursename": nom_cours,
        "categorie": texte_categorie,
    })

# 5. Afficher un petit bilan dans la console
print(f"BILAN DE L'EXTRACTION :")
print(f"- Total des cours extraits : {len(tous_les_cours)}")

# 6. Exporter TOUS les cours dans un fichier JSON
chemin_export = r"C:\Semestre8\ProjetAudit\Data\Audit_Scraping_Tous_Les_Cours_Moodle.json"
with open(chemin_export, 'w', encoding='utf-8') as f:
    json.dump(tous_les_cours, f, indent=4, ensure_ascii=False)

print(f"\n L'ensemble des cours a été sauvegardé dans le fichier : {chemin_export}")