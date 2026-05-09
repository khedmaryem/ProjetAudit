import json
import re
from pathlib import Path
from collections import Counter
from datetime import datetime


MOODLE_FILE = "data/Tous_Les_Cours_Moodle.json"
MAQUETTE_FILE = "data/MAQUETTE_IDU.json"

OUTPUT_FILE = "output/resultat_test_tracabilite_moodle_maquette.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def extract_maquette_modules():
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
            "ects": m["ects"],
            "cm": m["cm"],
            "td": m["td"],
            "tp": m["tp"]
        }

        by_full_code[full_code] = module
        by_short_code[short_code] = module

    return by_full_code, by_short_code


def extract_code_from_coursename(coursename):
    """
    Exemples :
    INFO731 Sécurité et Cryptographie -> INFO731
    DATA831_IDU- Big Data -> DATA831
    LANG801_PACY seuls -> LANG801
    """
    if not coursename:
        return None

    match = re.search(r"(?<![A-Z0-9])([A-Z]{2,8}\d{3})(?=[_\s\-]|$)", coursename.upper())

    if match:
        return match.group(1)

    return None


def is_idu_scope(course):
    text = f"{course.get('coursename', '')} {course.get('categorie', '')}".upper()

    if "INFORMATIONS IDU" in text:
        return False

    if "AUCUNE CATÉGORIE" in text:
        return False

    if "IGE3" in text or "IGE4" in text or "IGE5" in text:
        return True

    if "IDU3" in text or "IDU4" in text or "IDU5" in text:
        return True

    if "INFORMATIQUE, DONNÉES, USAGES" in text:
        return True

    if "INFORMATIQUE, DONNEES, USAGES" in text:
        return True

    if "COURS TRANSVERSAUX" in text:
        return True

    return False


def classify_course(course):
    text = f"{course.get('coursename', '')} {course.get('categorie', '')}".upper()

    if "COURS TRANSVERSAUX" in text:
        return "TRANSVERSAL"

    if (
        "IGE3" in text or "IGE4" in text or "IGE5" in text
        or "IDU3" in text or "IDU4" in text or "IDU5" in text
        or "INFORMATIQUE, DONNÉES, USAGES" in text
        or "INFORMATIQUE, DONNEES, USAGES" in text
    ):
        return "TEACHING_IDU"

    return "OUT_OF_SCOPE"


def infer_year(course):
    text = f"{course.get('coursename', '')} {course.get('categorie', '')}".upper()

    if "IDU3" in text or "IGE3" in text:
        return "IDU3"

    if "IDU4" in text or "IGE4" in text:
        return "IDU4"

    if "IDU5" in text or "IGE5" in text:
        return "IDU5"

    return None


def infer_semester(course):
    text = f"{course.get('coursename', '')} {course.get('categorie', '')}".upper()

    match = re.search(r"SEMESTRE\s*(\d+)", text)
    if match:
        return f"S{match.group(1)}"

    return None


def normalize_moodle_course(course, maquette_by_short):
    coursename = course.get("coursename", "").strip()
    categorie = course.get("categorie", "").strip()

    code = extract_code_from_coursename(coursename)

    exists = code in maquette_by_short if code else False
    module_ref = maquette_by_short.get(code) if code else None

    return {
        "coursename": coursename,
        "categorie": categorie,
        "moodle_code": code,
        "course_category": classify_course(course),
        "year": infer_year(course),
        "semester": infer_semester(course),
        "traceability": {
            "exists_in_maquette": exists,
            "official_code": module_ref["code_module"] if module_ref else None,
            "official_name": module_ref["nom"] if module_ref else None
        }
    }


def main():
    moodle_courses = load_json(MOODLE_FILE)
    _, maquette_by_short = extract_maquette_modules()

    # garder seulement le périmètre utile IDU/transversal
    scoped_courses = [
        c for c in moodle_courses
        if is_idu_scope(c)
    ]

    normalized_courses = [
        normalize_moodle_course(c, maquette_by_short)
        for c in scoped_courses
    ]

    teaching_or_transversal = [
    c for c in normalized_courses
    if c["course_category"] in ["TEACHING_IDU", "TRANSVERSAL"]
]

    traced_courses = [
        c for c in teaching_or_transversal
        if c["traceability"]["exists_in_maquette"] is True
    ]

    untraced_with_code = [
        c for c in teaching_or_transversal
        if c["moodle_code"] is not None
        and c["traceability"]["exists_in_maquette"] is False
    ]

    untraced_without_code = [
        c for c in teaching_or_transversal
        if c["moodle_code"] is None
    ]

    code_counter = Counter(c["moodle_code"] for c in untraced_with_code)

    simple_table = []

    for code, count in code_counter.most_common():
        examples = [
            {
                "coursename": c["coursename"],
                "categorie": c["categorie"],
                "year": c["year"],
                "semester": c["semester"],
                "course_category": c["course_category"]
            }
            for c in untraced_with_code
            if c["moodle_code"] == code
        ]

        simple_table.append({
            "code_moodle": code,
            "nombre": count,
            "probleme": "Absent de la maquette",
            "impact": "Traçabilité impossible",
            "interpretation": "Cours présent dans Moodle mais absent de la maquette officielle",
            "examples": examples[:3]
        })

    if untraced_without_code:
        simple_table.append({
            "code_moodle": "SANS_CODE",
            "nombre": len(untraced_without_code),
            "probleme": "Aucun code détecté",
            "impact": "Traçabilité impossible",
            "interpretation": "Cours Moodle sans code module exploitable",
            "examples": [
                {
                    "coursename": c["coursename"],
                    "categorie": c["categorie"],
                    "course_category": c["course_category"]
                }
                for c in untraced_without_code[:3]
            ]
        })

    moodle_module_codes = {
        c["moodle_code"]
        for c in teaching_or_transversal
        if c["moodle_code"] is not None
    }

    traced_module_codes = {
        c["moodle_code"]
        for c in traced_courses
        if c["moodle_code"] is not None
    }

    untraced_module_codes = {
        c["moodle_code"]
        for c in untraced_with_code
        if c["moodle_code"] is not None
    }

    traceability_rate_courses = round(
        len(traced_courses) / len(teaching_or_transversal) * 100, 2
    ) if teaching_or_transversal else 0

    traceability_rate_modules = round(
        len(traced_module_codes) / len(moodle_module_codes) * 100, 2
    ) if moodle_module_codes else 0

    report = {
        "audit_name": "Résultat de test - Traçabilité Moodle vers Maquette",
        "generated_at": datetime.now().isoformat(),

        "test_definition": {
            "dimension": "Traçabilité",
            "objective": "Vérifier que chaque cours Moodle lié à IDU peut être rattaché à un module officiel de la maquette.",
            "rule": "Un cours Moodle est traçable si son code extrait existe dans MAQUETTE_IDU.",
            "scope": "Cours Moodle IDU + cours transversaux."
        },

        "summary": {
            "total_moodle_courses_raw": len(moodle_courses),
            "total_courses_in_scope": len(scoped_courses),
            "total_teaching_or_transversal_courses": len(teaching_or_transversal),

            "courses_traced_to_maquette": len(traced_courses),
            "courses_not_traced_to_maquette": len(untraced_with_code),
            "courses_without_code": len(untraced_without_code),

            "distinct_moodle_modules": len(moodle_module_codes),
            "distinct_modules_traced": len(traced_module_codes),
            "distinct_modules_not_traced": len(untraced_module_codes),

            "traceability_rate_courses_percent": traceability_rate_courses,
            "traceability_rate_modules_percent": traceability_rate_modules,

            "top_untraced_codes": dict(code_counter.most_common(20))
        },

        "interpretation": {
            "main_result": "Certains cours Moodle existent sans correspondance dans la maquette officielle.",
            "audit_conclusion": "Il existe un défaut de traçabilité entre Moodle et la maquette pour les codes absents.",
            "business_impact": "Ces cours ne peuvent pas être reliés automatiquement à un module officiel, ce qui complique l’audit pédagogique."
        },

        "simple_result_table": simple_table,

        "normalized_courses": normalized_courses,

        "dashboard_ready": {
            "table_rows": [
                {
                    "code_moodle": row["code_moodle"],
                    "nombre": row["nombre"],
                    "probleme": row["probleme"],
                    "impact": row["impact"],
                    "interpretation": row["interpretation"]
                }
                for row in simple_table
            ]
        }
    }

    save_json(OUTPUT_FILE, report)

    print(f"Rapport généré : {OUTPUT_FILE}")
    print("Cours Moodle bruts :", len(moodle_courses))
    print("Cours dans périmètre :", len(scoped_courses))
    print("Cours traçables :", len(traced_courses))
    print("Cours non traçables :", len(untraced_with_code))
    print("Cours sans code :", len(untraced_without_code))
    print("Modules Moodle distincts :", len(moodle_module_codes))
    print("Modules traçables :", len(traced_module_codes))
    print("Modules non traçables :", len(untraced_module_codes))


if __name__ == "__main__":
    main()