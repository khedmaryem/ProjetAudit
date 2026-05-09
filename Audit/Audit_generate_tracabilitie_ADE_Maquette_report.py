import json
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime


INPUT_FILE = "output/ade_normalized.json"
OUTPUT_FILE = "output/resultat_test_tracabilite_ade_maquette.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def is_teaching(event):
    return event["session"]["category"] == "TEACHING"


def event_short(event):
    return {
        "source_year": event["source_year"],
        "title": event["title_raw"],
        "code_ade": event["module"]["short_code"],
        "type": event["session"]["type"],
        "date": event["session"]["date"],
        "start": event["session"]["start_time"],
        "end": event["session"]["end_time"],
        "duration_hours": event["session"]["duration_hours"],
        "teachers": event["people"]["teachers"],
        "idu_groups": event["groups"]["idu"],
        "rooms": event["location"]["room_names"]
    }


def generate_report():
    data = load_json(INPUT_FILE)
    events = data["events"]

    teaching_events = [e for e in events if is_teaching(e)]

    traced_events = [
        e for e in teaching_events
        if e["module"]["exists_in_maquette"] is True
    ]

    untraced_with_code = [
        e for e in teaching_events
        if e["module"]["short_code"] is not None
        and e["module"]["exists_in_maquette"] is False
    ]

    untraced_without_code = [
        e for e in teaching_events
        if e["module"]["short_code"] is None
    ]

    code_counter = Counter(
        e["module"]["short_code"]
        for e in untraced_with_code
    )

    examples_by_code = defaultdict(list)

    for e in untraced_with_code:
        code = e["module"]["short_code"]
        if len(examples_by_code[code]) < 3:
            examples_by_code[code].append(event_short(e))

    # Version simple pour tableau/dashboard
    simple_rows = []

    for code, count in code_counter.most_common():
        simple_rows.append({
            "code_ade": code,
            "nombre": count,
            "probleme": "Absent de la maquette",
            "impact": "Traçabilité impossible",
            "interpretation": "Présent dans ADE mais absent de la maquette officielle"
        })

    if untraced_without_code:
        simple_rows.append({
            "code_ade": "SANS_CODE",
            "nombre": len(untraced_without_code),
            "probleme": "Aucun code module détecté",
            "impact": "Traçabilité impossible",
            "interpretation": "Séance pédagogique sans code module exploitable"
        })

    # Version détaillée pour audit
    detailed_anomalies = []

    for code, count in code_counter.most_common():
        detailed_anomalies.append({
            "test_id": "TRACEABILITY_ADE_TO_MAQUETTE",
            "dimension": "Traçabilité",
            "severity": "MAJEUR",
            "status": "FAILED",
            "code_ade": code,
            "count_events": count,
            "problem": "Code présent dans ADE mais absent de la maquette officielle.",
            "impact": "Impossible de rattacher ces séances à une source pédagogique officielle.",
            "recommendation": "Vérifier si ce code doit être ajouté à la maquette ou corrigé dans ADE.",
            "examples": examples_by_code[code]
        })

    if untraced_without_code:
        detailed_anomalies.append({
            "test_id": "TRACEABILITY_MISSING_MODULE_CODE",
            "dimension": "Traçabilité",
            "severity": "MAJEUR",
            "status": "FAILED",
            "code_ade": None,
            "count_events": len(untraced_without_code),
            "problem": "Séances pédagogiques sans code module détectable.",
            "impact": "Impossible de relier ces séances à une source maquette.",
            "recommendation": "Normaliser les titres ADE pour inclure un code module.",
            "examples": [event_short(e) for e in untraced_without_code[:5]]
        })

    report = {
        "audit_name": "Résultat de test - Traçabilité ADE vers Maquette",
        "generated_at": datetime.now().isoformat(),

        "test_definition": {
            "dimension": "Traçabilité",
            "objective": "Vérifier que chaque séance pédagogique ADE peut être rattachée à un module officiel de la maquette.",
            "rule": "Une séance pédagogique est traçable si son code module ADE existe dans MAQUETTE_IDU.",
            "scope": "Uniquement les événements classés TEACHING."
        },

        "summary": {
            "total_teaching_events": len(teaching_events),
            "events_traced_to_maquette": len(traced_events),
            "events_not_traced_to_maquette": len(untraced_with_code),
            "events_without_code": len(untraced_without_code),
            "traceability_rate_percent": round(
                len(traced_events) / len(teaching_events) * 100, 2
            ) if teaching_events else 0,
            "top_untraced_codes": dict(code_counter.most_common(15))
        },

        "simple_result_table": simple_rows,

        "interpretation": {
            "main_result": "Des séances existent dans ADE sans source de référence dans la maquette.",
            "audit_conclusion": "Il s’agit d’un défaut de traçabilité entre ADE et la maquette officielle.",
            "business_impact": "Ces séances ne peuvent pas être reliées automatiquement à un module officiel ni utilisées de façon fiable pour comparer les heures prévues et planifiées."
        },

        "detailed_anomalies": detailed_anomalies,

        "dashboard_ready": {
            "table_rows": simple_rows,
            "top_untraced_codes": [
                {
                    "code_ade": code,
                    "nombre": count
                }
                for code, count in code_counter.most_common(15)
            ]
        }
    }

    save_json(OUTPUT_FILE, report)

    print(f"Rapport généré : {OUTPUT_FILE}")
    print(f"Événements pédagogiques : {len(teaching_events)}")
    print(f"Traçables vers maquette : {len(traced_events)}")
    print(f"Non traçables avec code : {len(untraced_with_code)}")
    print(f"Sans code : {len(untraced_without_code)}")


if __name__ == "__main__":
    generate_report()