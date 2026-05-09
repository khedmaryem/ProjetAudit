import json
import re
from pathlib import Path
from datetime import datetime
from collections import Counter

MAQUETTE_FILE = "data/MAQUETTE_IDU.json"

ADE_FILES = {
    "IDU3": "data/ADECal_IDU3.json",
    "IDU4": "data/ADECal_IDU4.json",
    "IDU5": "data/ADECal_IDU5.json",
}

OUTPUT_FILE = "output/ade_normalized.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def clean_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def load_maquette_modules():
    raw = load_json(MAQUETTE_FILE)

    modules = raw[2]["data"]

    by_full_code = {}
    by_short_code = {}

    for m in modules:
        full_code = m["code_module"]          # INFO631_IDU
        short_code = full_code.split("_")[0]  # INFO631

        module = {
            "code_module": full_code,
            "short_code": short_code,
            "nom": m["nom"],
            "ects": float(m["ects"]),
            "cm": float(m["cm"]),
            "td": float(m["td"]),
            "tp": float(m["tp"]),
        }

        by_full_code[full_code] = module
        by_short_code[short_code] = module

    return by_full_code, by_short_code


def parse_datetime(value):
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def duration_hours(start, end):
    if not start or not end:
        return 0
    return round((end - start).total_seconds() / 3600, 2)


def extract_rooms(location):
    """
    Exemple:
    A-C214 (32pl.) -> A-C214 + capacité 32
    A-C205 (30pl.),A-C204 (24pl.) -> 2 salles
    """
    if not location or not location.strip():
        return []

    rooms = []

    for part in location.split(","):
        part = part.strip()

        capacity = None
        cap_match = re.search(r"\((\d+)pl\.\)", part)
        if cap_match:
            capacity = int(cap_match.group(1))

        room_name = re.sub(r"\(.*?\)", "", part).strip()

        if room_name:
            rooms.append({
                "room": room_name,
                "capacity": capacity
            })

    return rooms


def extract_module_code(title, description, maquette_by_short):
    text = f"{title} {description}".upper()

    matches = re.findall(r"(?<![A-Z0-9])([A-Z]{2,8}\d{3})(?=[_\s\-]|$)", text)

    for code in matches:
        if code in maquette_by_short:
            return code, maquette_by_short[code], True

    if matches:
        return matches[0], None, False

    return None, None, False


def extract_session_type(description, title):
    """
    Priorité à la description car elle contient souvent (TD), (TP), (CM), etc.
    """
    text = f"{description} {title}".upper()

    type_match = re.search(r"\((CM|TD|TP|EXAMEN|EXAM|REUNION|RÉUNION|ACCUEIL-RENTREE|ACTIVITE NON ENCADREE|SOUTIEN)\)", text)

    if type_match:
        value = type_match.group(1)

        if value == "EXAMEN":
            return "EXAM"
        if value == "RÉUNION":
            return "REUNION"
        if value == "ACCUEIL-RENTREE":
            return "ACCUEIL"
        if value == "ACTIVITE NON ENCADREE":
            return "ACTIVITE_NON_ENCADREE"

        return value

    if "TOEIC" in text:
        return "EXAM"

    return "UNKNOWN"


def classify_event(title, session_type, module_found):
    text = title.upper()

    if session_type in ["REUNION", "ACCUEIL", "ACTIVITE_NON_ENCADREE"]:
        return "NON_TEACHING"

    if "RENTREE" in text or "RENTRÉE" in text:
        return "NON_TEACHING"

    if "REUNION" in text or "RÉUNION" in text:
        return "NON_TEACHING"

    if "BDE" in text or "BDS" in text or "CLUB" in text:
        return "NON_TEACHING"

    if "BUS" in text or "DEPLACEMENT" in text or "DÉPLACEMENT" in text:
        return "NON_TEACHING"

    if session_type in ["CM", "TD", "TP", "EXAM", "SOUTIEN"]:
        return "TEACHING"

    if module_found:
        return "TEACHING"

    return "UNKNOWN"

def extract_groups(description):
    lines = [l.strip() for l in description.splitlines() if l.strip()]
    groups = []

    group_patterns = [
        r"^IDU-\d.*",
        r"^MECA-[A-Z]+-\d.*",
        r"^SNI-\d.*",
        r"^EPU-\d.*",
        r"^PACY-\d.*",
    ]

    for line in lines:
        for pattern in group_patterns:
            if re.match(pattern, line):
                groups.append(line)
                break

    return list(dict.fromkeys(groups))


def extract_idu_groups(groups):
    return [g for g in groups if g.startswith("IDU-")]


def extract_teachers(description):
    lines = [l.strip() for l in description.splitlines() if l.strip()]
    teachers = []

    for line in lines:
        upper = line.upper()

        if "EXPORTÉ LE" in upper or "EXPORTE LE" in upper:
            continue

        if "," in line:
            continue

        if "(" in line or ")" in line:
            continue

        if re.match(r"^(IDU|MECA|SNI|EPU|PACY)-", line):
            continue

        if re.search(r"[A-Z]{2,8}\d{3}", line):
            continue

        if re.match(r"^\d+$", line):
            continue

        words = line.split()

        if len(words) >= 2 and all(w.upper() == w for w in words):
            teachers.append(line)

    return list(dict.fromkeys(teachers))


def normalize_event(raw, source_year, maquette_by_short):
    title = clean_text(raw.get("Title", ""))
    location = clean_text(raw.get("Location", ""))
    description = raw.get("Description", "")

    # On ignore les événements sans titre
    if not title:
        return None

    # On ignore les événements sans location si tu ne veux pas les prendre
    if not location:
        return None

    start_dt = parse_datetime(raw.get("Starts", ""))
    end_dt = parse_datetime(raw.get("Ends", ""))

    if not start_dt or not end_dt:
        return None

    module_short, module_info, module_found = extract_module_code(
        title,
        description,
        maquette_by_short
    )

    session_type = extract_session_type(description, title)
    event_category = classify_event(title, session_type, module_found)

    groups = extract_groups(description)
    idu_groups = extract_idu_groups(groups)
    teachers = extract_teachers(description)
    rooms = extract_rooms(location)

    return {
        "source_year": source_year,

        "title_raw": title,
        "description_raw": description,

        "module": {
            "short_code": module_short,
            "code_module": module_info["code_module"] if module_info else None,
            "name_from_maquette": module_info["nom"] if module_info else None,
            "exists_in_maquette": module_found,
        },

        "session": {
            "type": session_type,
            "category": event_category,
            "start": raw.get("Starts"),
            "end": raw.get("Ends"),
            "duration_hours": duration_hours(start_dt, end_dt),
            "date": start_dt.date().isoformat(),
            "start_time": start_dt.time().isoformat(),
            "end_time": end_dt.time().isoformat(),
        },

        "location": {
            "raw": location,
            "rooms": rooms,
            "room_names": [r["room"] for r in rooms],
        },

        "people": {
            "teachers": teachers,
        },

        "groups": {
            "all": groups,
            "idu": idu_groups,
        },

        "quality_flags": {
            "has_title": bool(title),
            "has_location": bool(location),
            "has_module_code": module_short is not None,
            "module_found_in_maquette": module_found,
            "has_session_type": session_type != "UNKNOWN",
            "has_teacher": len(teachers) > 0,
            "has_group": len(groups) > 0,
            "has_idu_group": len(idu_groups) > 0,
        }
    }


def main():
    _, maquette_by_short = load_maquette_modules()

    normalized_events = []
    ignored_events = []

    for source_year, file_path in ADE_FILES.items():
        events = load_json(file_path)

        for raw in events:
            normalized = normalize_event(raw, source_year, maquette_by_short)

            if normalized is None:
                ignored_events.append({
                    "source_year": source_year,
                    "reason": "EMPTY_TITLE_OR_LOCATION_OR_INVALID_DATE",
                    "title": raw.get("Title"),
                    "location": raw.get("Location"),
                    "starts": raw.get("Starts"),
                    "ends": raw.get("Ends"),
                })
            else:
                normalized_events.append(normalized)

    summary = {
        "total_normalized_events": len(normalized_events),
        "total_ignored_events": len(ignored_events),
        "events_by_source_year": dict(Counter(e["source_year"] for e in normalized_events)),
        "events_by_category": dict(Counter(e["session"]["category"] for e in normalized_events)),
        "events_by_session_type": dict(Counter(e["session"]["type"] for e in normalized_events)),
        "events_not_in_maquette": sum(
            1 for e in normalized_events
            if e["module"]["short_code"] and not e["module"]["exists_in_maquette"]
        ),
        "events_without_teacher": sum(
            1 for e in normalized_events
            if not e["quality_flags"]["has_teacher"]
        ),
        "events_without_idu_group": sum(
            1 for e in normalized_events
            if not e["quality_flags"]["has_idu_group"]
        ),
    }

    output = {
        "dataset_name": "ADE IDU normalized",
        "description": "Fichier intermédiaire propre pour l'audit qualité de l'emploi du temps IDU.",
        "generated_at": datetime.now().isoformat(),
        "input_files": ADE_FILES,
        "maquette_file": MAQUETTE_FILE,
        "summary": summary,
        "events": normalized_events,
        "ignored_events": ignored_events,
    }

    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)

    print(f"Fichier généré : {OUTPUT_FILE}")
    print(f"Événements normalisés : {len(normalized_events)}")
    print(f"Événements ignorés : {len(ignored_events)}")


if __name__ == "__main__":
    main()