
import json, csv, re, sys
from datetime import datetime

ORDRE = {
    'CM':   1,
    'TD':   2,
    'TP':   3,
    'Exam': 4,
    'PROJ': 5,
}

def criticite_par_types(type_avant, type_apres):
    
    paires_bloquantes = {('CM','TD'), ('CM','TP'), ('TD','TP')}
    if (type_avant, type_apres) in paires_bloquantes:
        return 'BLOQUANT'
    return 'MAJEUR'


def verifier_ordre(type_avant, num_avant, type_apres, num_apres):
    
    rang_av = ORDRE.get(type_avant, 99)
    rang_ap = ORDRE.get(type_apres, 99)

    if type_avant == type_apres:
        # Même type — vérifier l'ordre des numéros
        return num_avant > num_apres  # violation si num_avant > num_apres
    else:
        # Types différents — vérifier l'ordre des rangs
        return rang_av > rang_ap  # violation si rang_avant > rang_apres


# ─────────────────────────────────────────────
# LECTURE JSON (fichier de cohérence de steve)
# ─────────────────────────────────────────────
PATTERN_SOURCE1 = re.compile(
    r'([A-Z0-9_]+)\s*:\s*([A-Z][a-z]*)\s*n°(\d+)\s*->\s*([A-Z][a-z]*)\s*n°(\d+)',
    re.IGNORECASE
)
PATTERN_DATES = re.compile(r'(\d{4}-\d{2}-\d{2})\s+vs\s+(\d{4}-\d{2}-\d{2})')

def lire_json(chemin):
    with open(chemin, encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, list):
        entrees = data
    elif 'anomalies' in data:
        entrees = data['anomalies']
    else:
        entrees = [data]

    resultats = []
    for e in entrees:
        # Format cohérence : extraire depuis source_1 + description
        if 'source_1' in e:
            m1 = PATTERN_SOURCE1.search(e.get('source_1', ''))
            m2 = PATTERN_DATES.search(e.get('description', ''))
            if not m1:
                continue

            module     = m1.group(1)
            type_avant = m1.group(2).upper()
            num_avant  = int(m1.group(3))
            type_apres = m1.group(4).upper()
            num_apres  = int(m1.group(5))
            date_avant = m2.group(1) if m2 else None
            date_apres = m2.group(2) if m2 else None

        # Format conformité : colonnes directes
        elif 'type_avant' in e:
            module     = e['module']
            type_avant = e['type_avant'].upper()
            num_avant  = int(e['num_avant'])
            type_apres = e['type_apres'].upper()
            num_apres  = int(e['num_apres'])
            date_avant = e.get('date_avant')
            date_apres = e.get('date_apres')

        else:
            continue

        resultats.append({
            'module':     module,
            'type_avant': type_avant,
            'num_avant':  num_avant,
            'type_apres': type_apres,
            'num_apres':  num_apres,
            'date_avant': date_avant,
            'date_apres': date_apres,
        })

    return resultats



PATTERN_REGLE = re.compile(
    r'([A-Z]+)\s*(?:n°)?\s*(\d+)\s*(?:\u2192|->)\s*([A-Z]+)\s*(?:n°)?\s*(\d+)',
    re.IGNORECASE
)

def lire_csv(chemin):
    resultats = []
    with open(chemin, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            module = row.get('module', '').strip()

            # Extraire type+num depuis la colonne 'regle' ou 'erreur'
            texte = row.get('regle', '') or row.get('erreur', '')
            m = PATTERN_REGLE.search(texte)
            if not m:
                continue

            type_avant = m.group(1).upper()
            num_avant  = int(m.group(2))
            type_apres = m.group(3).upper()
            num_apres  = int(m.group(4))

            resultats.append({
                'module':     module,
                'type_avant': type_avant,
                'num_avant':  num_avant,
                'type_apres': type_apres,
                'num_apres':  num_apres,
                'date_avant': row.get('date_avant', ''),
                'date_apres': row.get('date_apres', ''),
            })

    return resultats


# ─────────────────────────────────────────────
# VÉRIFICATION DE L'ORDRE
# ─────────────────────────────────────────────

def verifier(entrees):
    violations  = []
    respectees  = []

    for e in entrees:
        type_av = e['type_avant']
        type_ap = e['type_apres']
        num_av  = e['num_avant']
        num_ap  = e['num_apres']

        est_violation = verifier_ordre(type_av, num_av, type_ap, num_ap)

        if est_violation:
            # Calculer l'écart si les dates sont disponibles
            ecart_h = None
            if e['date_avant'] and e['date_apres']:
                try:
                    fmt = '%Y-%m-%d' if '-' in e['date_avant'] else '%d/%m/%Y %H:%M'
                    d1  = datetime.strptime(e['date_avant'][:10], '%Y-%m-%d')
                    d2  = datetime.strptime(e['date_apres'][:10], '%Y-%m-%d')
                    ecart_h = round(abs((d1 - d2).total_seconds() / 3600), 1)
                except:
                    ecart_h = None

            violations.append({
                'module':      e['module'],
                'regle':       f"{type_av}{num_av} → {type_ap}{num_ap}",
                'type_avant':  type_av,
                'num_avant':   num_av,
                'type_apres':  type_ap,
                'num_apres':   num_ap,
                'date_avant':  e['date_avant'],
                'date_apres':  e['date_apres'],
                'ecart_h':     ecart_h,
                'criticite':   criticite_par_types(type_av, type_ap),
                'explication': (
                    f"VIOLATION : {type_av} n°{num_av} doit précéder {type_ap} n°{num_ap} "
                    f"(rang {ORDRE.get(type_av,'?')} > rang {ORDRE.get(type_ap,'?')})"
                    if type_av != type_ap else
                    f"VIOLATION : {type_av} n°{num_av} doit précéder {type_av} n°{num_ap} "
                    f"(numéro {num_av} > {num_ap})"
                )
            })
        else:
            respectees.append(e)

    return violations, respectees


# ─────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────

def exporter(violations, respectees, chemin_out='conformite_verifie.json'):
    nb_bloc = sum(1 for v in violations if v['criticite'] == 'BLOQUANT')
    nb_maj  = sum(1 for v in violations if v['criticite'] == 'MAJEUR')
    total   = len(violations) + len(respectees)

    rapport = {
        'total_verifie':   total,
        'nb_violations':   len(violations),
        'nb_respectees':   len(respectees),
        'nb_bloquant':     nb_bloc,
        'nb_majeur':       nb_maj,
        'taux_conformite': round(len(respectees) / total * 100, 1) if total else 0,
        'ordre_attendu':   'CM(1) → TD(2) → TP(3) → Exam(4) → PROJ(5)',
        'violations':      sorted(violations, key=lambda x: (
            0 if x['criticite'] == 'BLOQUANT' else 1,
            -(x['ecart_h'] or 0)
        )),
    }

    with open(chemin_out, 'w', encoding='utf-8') as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2)

    print(f"\n  → {chemin_out} exporté")
    return rapport




def exporter_csv(violations, chemin_out='conformite_verifie.csv'):
    """Export CSV directement importable dans Power BI"""
    import csv
    colonnes = ['module', 'regle', 'type_avant', 'num_avant',
                'type_apres', 'num_apres', 'date_avant', 'date_apres',
                'ecart_h', 'criticite', 'explication']
    with open(chemin_out, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=colonnes)
        writer.writeheader()
        for v in violations:
            writer.writerow({k: v.get(k, '') for k in colonnes})
    print(f"  → {chemin_out} exporté ({len(violations)} violations)")

# ─────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Fichier en argument ou par défaut
    if len(sys.argv) > 1:
        fichier = sys.argv[1]
    else:
        # Essaie les fichiers connus dans l'ordre
        import os
        for candidat in [
            'sequence_chronologie_anomalies.json',
            'conformite_from_coherence.json',
            'anomalies_conformite.json',
            'anomalies_conformite.csv',
        ]:
            if os.path.exists(candidat):
                fichier = candidat
                break
        else:
            print("Aucun fichier trouvé. Usage : python verifier_conformite.py <fichier.json|csv>")
            sys.exit(1)

    print(f"\n=== Vérificateur d'ordre pédagogique IDU ===")
    print(f"Fichier : {fichier}")
    print(f"Ordre attendu : CM → TD → TP → Exam → PROJ\n")

    # Lire selon l'extension
    if fichier.endswith('.csv'):
        entrees = lire_csv(fichier)
    else:
        entrees = lire_json(fichier)

    print(f"1. {len(entrees)} entrées lues")

    # Vérifier
    violations, respectees = verifier(entrees)

    print(f"2. Résultats :")
    print(f"   ✓ Conformes  : {len(respectees)}")
    print(f"   ✗ Violations : {len(violations)}")
    print(f"     dont BLOQUANT : {sum(1 for v in violations if v['criticite']=='BLOQUANT')}")
    print(f"     dont MAJEUR   : {sum(1 for v in violations if v['criticite']=='MAJEUR')}")

    # Afficher les violations bloquantes
    bloquants = [v for v in violations if v['criticite'] == 'BLOQUANT']
    if bloquants:
        print(f"\n--- Violations BLOQUANTES ---")
        for v in bloquants[:10]:
            ecart = f"  ({v['ecart_h']}h)" if v['ecart_h'] else ""
            print(f"  ❌ {v['module']} | {v['regle']}{ecart}")
            print(f"     {v['explication']}")

    # Exporter
    nom_out = fichier.split('/')[-1].split('\\')[-1].replace('.json','_verifie.json').replace('.csv','_verifie.json')
    rapport = exporter(violations, respectees, nom_out)
    nom_csv = nom_out.replace('.json', '.csv')
    exporter_csv(violations, nom_csv)

    print(f"\n=== Résumé ===")
    print(f"  Taux de conformité : {rapport['taux_conformite']}%")
    print(f"  Fichier exporté    : {nom_out}")