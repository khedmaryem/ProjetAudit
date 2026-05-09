import json
from pathlib import Path
import matplotlib.pyplot as plt

DATA_DIR = Path("Audit IDU")
FIGURES_DIR = DATA_DIR / "figures_exactitude"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

MODULES_ERREURS_FILE = DATA_DIR / "modules_avec_erreurs.json"

ADE_FILES = [
    DATA_DIR / "ADECal_IDU3.json",
    DATA_DIR / "ADECal_IDU4.json",
    DATA_DIR / "ADECal_IDU5.json"
]

# =========================
# 1. Lire modules avec erreurs
# =========================

with open(MODULES_ERREURS_FILE, "r", encoding="utf-8") as f:
    erreurs_data = json.load(f)

nombre_anomalies = len(erreurs_data["modules"])



total_adecal = 58

nombre_conformes = total_adecal - nombre_anomalies

taux_anomalies = (nombre_anomalies / total_adecal) * 100
taux_exactitude = (nombre_conformes / total_adecal) * 100


labels = [
    f"Anomalies d'exactitude\n{nombre_anomalies} ({taux_anomalies:.1f}%)",
    f"Données exactes\n{nombre_conformes} ({taux_exactitude:.1f}%)"
]

values = [nombre_anomalies, nombre_conformes]

plt.figure(figsize=(8, 8))

plt.pie(
    values,
    labels=labels,
    autopct="%1.1f%%",
    startangle=90,
    wedgeprops={"width": 0.4}
)

plt.title("Taux d'exactitude des données ADECal")

plt.tight_layout()

output_file = FIGURES_DIR / "donut_exactitude_adecal.png"
plt.savefig(output_file, dpi=300)
plt.show()

print("Nombre total ADECal :", total_adecal)
print("Nombre d'anomalies :", nombre_anomalies)
print("Nombre de données exactes :", nombre_conformes)
print("Taux d'anomalies :", round(taux_anomalies, 2), "%")
print("Taux d'exactitude :", round(taux_exactitude, 2), "%")
print("Figure sauvegardée :", output_file)