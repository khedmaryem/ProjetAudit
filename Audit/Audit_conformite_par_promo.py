"""
Lance l'audit séparément par promo pour avoir les vrais % par IDU3/4/5

Usage :
    python conformite_par_promo.py
"""

import json, re, sys
from datetime import datetime
from collections import defaultdict

# ── Copie exacte de tes fonctions depuis conformite.py ──

def charger_dependances(chemin):
    with open(chemin, encoding='utf-8') as f:
        contenu = json.load(f)
    arcs = contenu[2]["data"]
    return arcs

def extraire_prefixe_ade(title):
    m = re.split(r'_(CM|TDG|TD|TPG|TP\d*|ET|CT|EXAM)\b', title, flags=re.IGNORECASE, maxsplit=1)
    return m[0].strip()

def construire_code_map(arcs, chemins_ade):
    modules_dep = set()
    for arc in arcs:
        modules_dep.add(arc['module_precedent'])
        modules_dep.add(arc['module_suivant'])
    code_map = {}
    for chemin in chemins_ade:
        with open(chemin, encoding='utf-8') as f:
            evenements = json.load(f)
        for ev in evenements:
            prefixe = extraire_prefixe_ade(ev['Title'])
            if prefixe in code_map: continue
            m = re.match(r'([A-Z]+\d+)', prefixe)
            if not m: continue
            base = m.group(1)
            candidats = [mod for mod in modules_dep if mod.startswith(base)]
            if len(candidats) == 1:
                code_map[prefixe] = candidats[0]
    return code_map

def extraire_code_et_type(title, code_map):
    prefixe = extraire_prefixe_ade(title)
    code_canon = code_map.get(prefixe)
    if not code_canon: return None, None
    t = title.upper()
    if '_CM' in t: return code_canon, 'CM'
    if '_TD' in t: return code_canon, 'TD'
    if '_TP' in t: return code_canon, 'TP'
    if 'EXAM' in t or '_ET_' in t or '_CT' in t: return code_canon, 'Exam'
    if 'PROJ' in t: return code_canon, 'PROJ'
    return None, None

def construire_index(chemins_ade, code_map):
    groupes = defaultdict(list)
    for chemin in chemins_ade:
        with open(chemin, encoding='utf-8') as f:
            evenements = json.load(f)
        for ev in evenements:
            code, stype = extraire_code_et_type(ev['Title'], code_map)
            if code:
                date = datetime.fromisoformat(ev['Starts'].replace('Z', '+00:00'))
                groupes[(code, stype)].append(date)
    index = {}
    for (code, stype), dates in groupes.items():
        for i, date in enumerate(sorted(set(dates)), start=1):
            index[(code, stype, i)] = date
    return index

def verifier_conformite(arcs, index):
    anomalies = []
    ok_count = 0
    for arc in arcs:
        cle_av = (arc['module_precedent'], arc['type_precedent'], int(arc['numero_precedent']))
        cle_ap = (arc['module_suivant'],   arc['type_suivant'],   int(arc['numero_suivant']))
        date_av = index.get(cle_av)
        date_ap = index.get(cle_ap)
        if not date_av or not date_ap:
            continue
        if date_av > date_ap:
            criticite = 'BLOQUANT' if (cle_av[1]=='CM' and cle_ap[1] in ['TD','TP']) else 'MAJEUR'
            anomalies.append({
                'module':     cle_av[0],
                'erreur':     f"Inversion : {cle_av[1]}{cle_av[2]} après {cle_ap[1]}{cle_ap[2]}",
                'criticite':  criticite,
                'ecart_h':    round((date_av - date_ap).total_seconds() / 3600, 1),
            })
        else:
            ok_count += 1
    return anomalies, ok_count

# ─────────────────────────────────────────────
# AUDIT PAR PROMO
# ─────────────────────────────────────────────

if __name__ == "__main__":
    CHEMIN_DEP = "dependance_sequence_IDU.json"
    arcs = charger_dependances(CHEMIN_DEP)

    PROMOS = {
        'IDU3': ['ADECal_IDU3.json'],
        'IDU4': ['ADECal_IDU4.json'],
        'IDU5': ['ADECal_IDU5.json'],
    }

    print("\n=== Audit Conformité par Promo ===\n")
    print(f"{'Promo':<8} {'Vérifiés':>10} {'Conformes':>10} {'Violations':>12} {'Taux':>8}")
    print("-" * 52)

    resultats = {}
    for promo, fichiers in PROMOS.items():
        code_map = construire_code_map(arcs, fichiers)
        index    = construire_index(fichiers, code_map)
        anomalies, ok = verifier_conformite(arcs, index)

        total  = ok + len(anomalies)
        taux   = round(ok / total * 100, 1) if total else 0
        resultats[promo] = {'ok': ok, 'viol': len(anomalies), 'total': total, 'taux': taux}

        print(f"{promo:<8} {total:>10} {ok:>10} {len(anomalies):>12} {taux:>7}%")

    # Global
    total_g = sum(r['total'] for r in resultats.values())
    ok_g    = sum(r['ok']    for r in resultats.values())
    viol_g  = sum(r['viol']  for r in resultats.values())
    taux_g  = round(ok_g / total_g * 100, 1) if total_g else 0
    print("-" * 52)
    print(f"{'GLOBAL':<8} {total_g:>10} {ok_g:>10} {viol_g:>12} {taux_g:>7}%")

    print("\n✓ Résultats détaillés par promo affichés ci-dessus")