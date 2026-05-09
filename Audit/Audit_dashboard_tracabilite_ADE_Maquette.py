import json
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

BASE_DIR = Path(__file__).resolve().parent

REPORT_FILE = BASE_DIR / "output" / "resultat_test_tracabilite_ade_maquette.json"
NORMALIZED_FILE = BASE_DIR / "output" / "ade_normalized.json"
OUT_DIR = BASE_DIR / "output" / "dashboard_tracabilite_ade_maquette"
OUT_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.family"] = "DejaVu Sans"
COLOR_OK = "#2E7D32"
COLOR_KO = "#C62828"
COLOR_BLUE = "#1565C0"
COLOR_ORANGE = "#EF6C00"
COLOR_DARK = "#263238"


def save_fig(fig, filename):
    path = OUT_DIR / filename
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("Image sauvegardée :", path)


with open(REPORT_FILE, "r", encoding="utf-8") as f:
    report = json.load(f)

with open(NORMALIZED_FILE, "r", encoding="utf-8") as f:
    normalized = json.load(f)

summary = report["summary"]
table_rows = pd.DataFrame(report["dashboard_ready"]["table_rows"])
top_codes = pd.DataFrame(report["dashboard_ready"]["top_untraced_codes"])

teaching_events = [
    e for e in normalized["events"]
    if e["session"]["category"] == "TEACHING"
]

ade_modules = {
    e["module"]["short_code"]
    for e in teaching_events
    if e["module"]["short_code"] is not None
}

traced_modules = {
    e["module"]["short_code"]
    for e in teaching_events
    if e["module"]["short_code"] is not None
    and e["module"]["exists_in_maquette"] is True
}

untraced_modules = {
    e["module"]["short_code"]
    for e in teaching_events
    if e["module"]["short_code"] is not None
    and e["module"]["exists_in_maquette"] is False
}

without_code_events = [
    e for e in teaching_events
    if e["module"]["short_code"] is None
]

total_modules = len(ade_modules)
traced_count = len(traced_modules)
untraced_count = len(untraced_modules)
rate = round(traced_count / total_modules * 100, 2) if total_modules else 0


# =========================
# 1. KPI améliorés
# =========================

fig, ax = plt.subplots(figsize=(16, 5))
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")

fig.suptitle(
    "KPI - Traçabilité ADE vers Maquette",
    fontsize=20,
    fontweight="bold",
    color=COLOR_DARK,
    y=0.98
)

kpis = [
    ("Modules ADE distincts", total_modules, COLOR_BLUE),
    ("Modules traçables", traced_count, COLOR_OK),
    ("Modules non traçables", untraced_count, COLOR_KO),
    ("Taux modules", f"{rate}%", COLOR_ORANGE),
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

save_fig(fig, "01_kpi_ade_maquette_ameliore.png")


# =========================
# 2. Donut modules amélioré
# =========================

fig, ax = plt.subplots(figsize=(8, 7))

labels = ["Modules traçables", "Modules non traçables"]
values = [traced_count, untraced_count]
colors = [COLOR_OK, COLOR_KO]

ax.pie(
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

ax.set_title("Répartition des modules ADE distincts", fontsize=15, fontweight="bold", pad=20)
save_fig(fig, "02_donut_modules_ade_ameliore.png")


# =========================
# 3. Bar séances traçables / non traçables
# =========================

fig, ax = plt.subplots(figsize=(9, 6))

labels = ["Séances traçables", "Séances non traçables"]
values = [
    summary["events_traced_to_maquette"],
    summary["events_not_traced_to_maquette"]
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

ax.set_title("Traçabilité des séances ADE", fontsize=15, fontweight="bold", pad=15)
ax.set_ylabel("Nombre de séances")
ax.grid(axis="y", linestyle="--", alpha=0.4)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

save_fig(fig, "03_bar_seances_tracabilite_ameliore.png")


# =========================
# 4. Top codes ADE non traçables
# =========================

df_top = top_codes.sort_values("nombre", ascending=True).tail(12)

fig, ax = plt.subplots(figsize=(11, 7))

bars = ax.barh(
    df_top["code_ade"],
    df_top["nombre"],
    color=COLOR_ORANGE
)

for bar in bars:
    w = bar.get_width()
    ax.text(
        w + 0.5,
        bar.get_y() + bar.get_height() / 2,
        int(w),
        va="center",
        fontsize=10,
        fontweight="bold"
    )

ax.set_title("Top codes ADE non traçables", fontsize=15, fontweight="bold", pad=15)
ax.set_xlabel("Nombre de séances")
ax.set_ylabel("Code ADE")
ax.grid(axis="x", linestyle="--", alpha=0.4)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

save_fig(fig, "04_top_codes_ade_non_tracables_ameliore.png")


# =========================
# 5. Table améliorée
# =========================

table_df = table_rows[["code_ade", "nombre", "impact"]].copy()
table_df.columns = ["Code ADE", "Nb séances", "Impact"]
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
        cell.set_facecolor("#F2F2F2" if row % 2 == 0 else "white")

ax.set_title(
    "Codes ADE non traçables vers la maquette",
    fontsize=16,
    fontweight="bold",
    color=COLOR_DARK,
    pad=20
)

save_fig(fig, "05_table_ade_non_tracables_ameliore.png")

print("Dashboard amélioré généré dans :", OUT_DIR)