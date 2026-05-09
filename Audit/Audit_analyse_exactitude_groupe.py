import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict


DATA_DIR = Path("Audit IDU")

ADE_FILES = {
    "IDU3": DATA_DIR / "ADECal_IDU3.json",
    "IDU4": DATA_DIR / "ADECal_IDU4.json",
    "IDU5": DATA_DIR / "ADECal_IDU5.json",
}

OUTPUT_FILE = DATA_DIR / "rapport_exactitude_groupes_G1_G2.json"


def normalize_code(title):
    if not title:
        return ""

    title = title.strip().upper()
    first_part = title.split("_")[0]
    first_part = re.sub(r"[^A-Z0-9]", "", first_part)

    return first_part


def parse_datetime(date_str):
    return datetime.fromisoformat(date_str.replace("Z", "+00:00"))


def get_duration_hours(event):
    start = parse_datetime(event["Starts"])
    end = parse_datetime(event["Ends"])
    return (end - start).total_seconds() / 3600


def detect_type(title, description):
    text = f"{title} {description}".upper()

    if "EXAMEN" in text or "_CC" in text or "_ET" in text or "_CT" in text:
        return "EXAMEN"

    if "(TP)" in text or "TPG" in text or "_TP" in text:
        return "TP"

    if "(TD)" in text or "TDG" in text or "_TD" in text:
        return "TD"

    if "(CM)" in text or "_CM" in text:
        return "CM"

    if "(PROJET)" in text or "PROJET" in text:
        return "PROJET"

    return "AUTRE"


def detect_group(title, description):
    text = f"{title} {description}".upper()

    if re.search(r"IDU-\d+-G1\b|TPG1\b|TDG1\b|_G1\b", text):
        return "G1"

    if re.search(r"IDU-\d+-G2\b|TPG2\b|TDG2\b|_G2\b", text):
        return "G2"

    return None


def load_ade_events():
    all_events = []

    for niveau, file_path in ADE_FILES.items():
        with open(file_path, "r", encoding="utf-8") as f:
            events = json.load(f)

        for event in events:
            event["niveau"] = niveau
            all_events.append(event)

    return all_events


def analyze_g1_g2_exactitude():
    events = load_ade_events()

    heures_groupes = defaultdict(lambda: {
        "G1": defaultdict(float),
        "G2": defaultdict(float),
    })

    seen_sessions = set()

    for event in events:
        title = event.get("Title", "")
        description = event.get("Description", "")

        code = normalize_code(title)
        type_seance = detect_type(title, description)
        group = detect_group(title, description)

        if not code or group not in ["G1", "G2"]:
            continue

        duration = get_duration_hours(event)

        start = event.get("Starts")
        end = event.get("Ends")

        session_key = (
            code,
            type_seance,
            group,
            title,
            start,
            end,
        )

        if session_key in seen_sessions:
            continue

        seen_sessions.add(session_key)

        heures_groupes[code][group][type_seance] += duration

    result = {
        "summary": {
            "modules_avec_g1_g2": 0,
            "modules_equilibres": 0,
            "modules_non_equilibres": 0
        },
        "modules": []
    }

    types = ["CM", "TD", "TP", "EXAMEN", "PROJET"]

    for code, groups in heures_groupes.items():
        comparaison = {}
        module_has_g1_g2 = False
        module_ok = True

        for t in types:
            h_g1 = groups["G1"].get(t, 0)
            h_g2 = groups["G2"].get(t, 0)

            if h_g1 > 0 or h_g2 > 0:
                ecart = h_g1 - h_g2
                ok = abs(ecart) < 0.001

                comparaison[t] = {
                    "heures_G1": h_g1,
                    "heures_G2": h_g2,
                    "ecart": ecart,
                    "statut": "OK" if ok else "NON_EQUIVALENT"
                }

                if h_g1 > 0 and h_g2 > 0:
                    module_has_g1_g2 = True

                if not ok:
                    module_ok = False

        if comparaison:
            if module_has_g1_g2:
                result["summary"]["modules_avec_g1_g2"] += 1

                if module_ok:
                    result["summary"]["modules_equilibres"] += 1
                else:
                    result["summary"]["modules_non_equilibres"] += 1

            result["modules"].append({
                "code_module": code,
                "comparaison_groupes": comparaison,
                "statut_global": "OK" if module_ok else "NON_EQUIVALENT"
            })

    return result


def save_json(data, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print("Rapport généré :", output_file)


if __name__ == "__main__":
    report = analyze_g1_g2_exactitude()
    save_json(report, OUTPUT_FILE)

    print("Modules avec G1 et G2 :", report["summary"]["modules_avec_g1_g2"])
    print("Modules équilibrés :", report["summary"]["modules_equilibres"])
    print("Modules non équilibrés :", report["summary"]["modules_non_equilibres"])