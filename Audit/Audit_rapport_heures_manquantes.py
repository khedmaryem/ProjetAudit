import json
import os

def save_hours_json(report):
    output_dir = "Audit IDU"
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, "rapport_heures_manquantes.json")

    types = ["CM", "TD", "TP", "PROJET"]

    data_visualisation = []

    for module in report["modules"]:
        for t in types:
            data_visualisation.append({
                "code_module": module["code_module"],
                "type_seance": t,
                "heures_maquette": module.get("heures_maquette", {}).get(t, 0),
                "heures_ADE": module.get("heures_planifiees_ADE", {}).get(t, 0),
                "heures_manquantes": module.get("heures_manquantes", {}).get(t, 0),
                "heures_en_trop": module.get("heures_en_trop", {}).get(t, 0)
            })

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data_visualisation, f, ensure_ascii=False, indent=4)

    print("JSON généré :", output_file)