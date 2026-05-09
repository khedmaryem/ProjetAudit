import json
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = BASE_DIR / "output" / "resultat_test_tracabilite_moodle_maquette.json"
OUT_DIR = BASE_DIR / "output" / "dashboard_moodle_maquette"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# Style global
# =========================

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.titlesize"] = 15
plt.rcParams["axes.titleweight"] = "bold"
plt.rcParams["axes.labelsize"] = 11
plt.rcParams["xtick.labelsize"] = 10
plt.rcParams["ytick.labelsize"] = 10

COLOR_OK = "#2E7D32"
COLOR_KO = "#C62828"
COLOR_BLUE = "#1565C0"
COLOR_ORANGE = "#EF6C00"
COLOR_GREY = "#F5F5F5"
COLOR_DARK = "#263238"


def save_fig(fig, filename):
    path = OUT_DIR / filename
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Image sauvegardée :", path)


with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

summary = data["summary"]
courses = pd.DataFrame(data["normalized_courses"])
table_rows = pd.DataFrame(data["dashboard_ready"]["table_rows"])

courses["is_traced"] = courses["traceability"].apply(
    lambda x: x["exists_in_maquette"]
)

# =========================
# 1. KPI améliorés
# =========================

fig, ax = plt.subplots(figsize=(16, 5))
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")

fig.suptitle(
    "KPI - Traçabilité Moodle vers Maquette",
    fontsize=20,
    fontweight="bold",
    color=COLOR_DARK,
    y=0.98
)

kpis = [
    ("Modules analysés", summary["total_courses_in_scope"], COLOR_BLUE),
    ("Modules traçables", summary["courses_traced_to_maquette"], COLOR_OK),
    ("Modules non traçables", summary["courses_not_traced_to_maquette"], COLOR_KO),
    ("Taux modules", f'{summary["traceability_rate_modules_percent"]}%', COLOR_ORANGE),
]

card_width = 0.17
card_height = 0.55
start_x = 0.035
gap = 0.025
y = 0.25

for i, (label, value, color) in enumerate(kpis):
    x = start_x + i * (card_width + gap)

    card = FancyBboxPatch(
        (x, y),
        card_width,
        card_height,
        boxstyle="round,pad=0.015,rounding_size=0.03",
        linewidth=1.2,
        edgecolor="#DDDDDD",
        facecolor="#FFFFFF"
    )
    ax.add_patch(card)

    ax.text(
        x + card_width / 2,
        y + 0.35,
        str(value),
        ha="center",
        va="center",
        fontsize=28,
        fontweight="bold",
        color=color
    )

    ax.text(
        x + card_width / 2,
        y + 0.15,
        label,
        ha="center",
        va="center",
        fontsize=11,
        color=COLOR_DARK
    )

save_fig(fig, "01_kpi_moodle_maquette_ameliore.png")

# =========================
# 2. Donut modules amélioré
# =========================

fig, ax = plt.subplots(figsize=(8, 7))

labels = ["Modules traçables", "Modules non traçables"]
values = [
    summary["distinct_modules_traced"],
    summary["distinct_modules_not_traced"]
]
colors = [COLOR_OK, COLOR_KO]

wedges, texts, autotexts = ax.pie(
    values,
    labels=labels,
    autopct="%1.1f%%",
    startangle=90,
    colors=colors,
    pctdistance=0.75,
    textprops={"fontsize": 11}
)

centre_circle = plt.Circle((0, 0), 0.55, fc="white")
ax.add_artist(centre_circle)

total_modules = sum(values)
ax.text(
    0,
    0,
    f"{total_modules}\nmodules",
    ha="center",
    va="center",
    fontsize=18,
    fontweight="bold",
    color=COLOR_DARK
)

ax.set_title("Répartition des modules Moodle distincts", pad=20)
save_fig(fig, "02_donut_modules_moodle_ameliore.png")

# =========================
# 3. Bar cours par traçabilité amélioré
# =========================

fig, ax = plt.subplots(figsize=(9, 6))

labels = ["Cours traçables", "Cours non traçables"]
values = [
    summary["courses_traced_to_maquette"],
    summary["courses_not_traced_to_maquette"]
]
colors = [COLOR_OK, COLOR_KO]

bars = ax.bar(labels, values, color=colors, width=0.5)

for bar in bars:
    h = bar.get_height()
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        h + max(values) * 0.02,
        int(h),
        ha="center",
        fontsize=13,
        fontweight="bold"
    )

ax.set_title("Traçabilité des cours Moodle", pad=15)
ax.set_ylabel("Nombre de cours")
ax.grid(axis="y", linestyle="--", alpha=0.4)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

save_fig(fig, "03_bar_cours_tracabilite_ameliore.png")

# =========================
# 4. Traçabilité par catégorie améliorée
# =========================

grouped = courses.groupby(["course_category", "is_traced"]).size().unstack(fill_value=0)
grouped = grouped.rename(columns={True: "Traçables", False: "Non traçables"})

fig, ax = plt.subplots(figsize=(10, 6))

grouped.plot(
    kind="bar",
    stacked=True,
    ax=ax,
    color=[COLOR_KO, COLOR_OK]
)

ax.set_title("Traçabilité par catégorie de cours", pad=15)
ax.set_xlabel("Catégorie")
ax.set_ylabel("Nombre de cours")
ax.legend(title="Statut")
ax.grid(axis="y", linestyle="--", alpha=0.4)
plt.xticks(rotation=0)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

save_fig(fig, "04_bar_tracabilite_par_categorie_ameliore.png")

# =========================
# 5. Top codes non traçables amélioré
# =========================

top = table_rows.sort_values("nombre", ascending=True).tail(12)

fig, ax = plt.subplots(figsize=(11, 7))

bars = ax.barh(
    top["code_moodle"],
    top["nombre"],
    color=COLOR_ORANGE
)

for bar in bars:
    w = bar.get_width()
    ax.text(
        w + 0.1,
        bar.get_y() + bar.get_height() / 2,
        int(w),
        va="center",
        fontsize=10,
        fontweight="bold"
    )

ax.set_title("Top codes Moodle non traçables", pad=15)
ax.set_xlabel("Nombre de cours")
ax.set_ylabel("Code Moodle")
ax.grid(axis="x", linestyle="--", alpha=0.4)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

save_fig(fig, "05_top_codes_moodle_non_tracables_ameliore.png")

# =========================
# 6. Table améliorée
# =========================

table_df = table_rows[["code_moodle", "nombre", "impact"]].copy()
table_df.columns = ["Code Moodle", "Nb cours", "Impact"]
table_df = table_df.head(15)

fig, ax = plt.subplots(figsize=(12, 7))
ax.axis("off")

table = ax.table(
    cellText=table_df.values,
    colLabels=table_df.columns,
    loc="center",
    cellLoc="center",
    colLoc="center"
)

table.auto_set_font_size(False)
table.set_fontsize(10)
table.scale(1, 1.7)

for (row, col), cell in table.get_celld().items():
    if row == 0:
        cell.set_text_props(weight="bold", color="white")
        cell.set_facecolor(COLOR_BLUE)
    else:
        if row % 2 == 0:
            cell.set_facecolor("#F2F2F2")
        else:
            cell.set_facecolor("white")

ax.set_title(
    "Cours Moodle non traçables vers la maquette",
    fontsize=16,
    fontweight="bold",
    color=COLOR_DARK,
    pad=20
)

save_fig(fig, "06_table_moodle_non_tracables_ameliore.png")

print("Dashboard amélioré généré dans :", OUT_DIR)