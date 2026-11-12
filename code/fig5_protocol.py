# Fig. 5: the blind-repeat-route screening protocol (diagram)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

INK = "#1f1f1f"; INK2 = "#5f5f5f"; BLUE = "#2a78d6"; ORANGE = "#eb6834"; GREEN = "#1baf7a"; GREY = "#f2f2f2"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
fig, ax = plt.subplots(figsize=(11, 4.2))
ax.set_xlim(0, 112); ax.set_ylim(0, 42); ax.axis("off")


def box(x, y, w, h, title, body, edge, fill="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", lw=1.6, ec=edge, fc=fill))
    ax.text(x + w / 2, y + h - 2.6, title, ha="center", va="top", fontsize=10.5, fontweight="bold", color=INK)
    ax.text(x + w / 2, y + h - 7.4, body, ha="center", va="top", fontsize=8.6, color=INK, linespacing=1.35)


def arrow(x1, y1, x2, y2, label=None, lx=0, ly=0):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=13, lw=1.4, color=INK2))
    if label:
        ax.text((x1 + x2) / 2 + lx, (y1 + y2) / 2 + ly, label, ha="center", va="center", fontsize=9, color=INK2)


# input
box(0.5, 22, 15, 14, "Resume x", "job description J\ncutoff c", INK2, GREY)
# steps
box(20, 22, 24, 14, "1  Blind", "remove fields not needed\nto judge capability\n(birth date, marital status)", BLUE)
box(48.5, 22, 24, 14, "2  Repeat", "score the blind resume\nR times with the LLM;\nmean score s̄", BLUE)
box(77, 22, 24, 14, "3  Route", "is |s̄ − c| < δ ?", BLUE)
arrow(16.3, 29, 19.6, 29); arrow(44.8, 29, 48.1, 29); arrow(73.3, 29, 76.6, 29)
# outcomes
box(62, 1.5, 23, 11.5, "Human review", "borderline cases\n(est. 9% of applicants)", ORANGE)
box(89, 1.5, 22, 11.5, "Automatic decision", "invite if s̄ ≥ c\nreject if s̄ < c", GREEN)
arrow(84, 21.4, 76, 13.6, "yes", lx=-2.4, ly=0.6)
arrow(94, 21.4, 100, 13.6, "no", lx=2.4, ly=0.6)
# what each step addresses
for x, txt in [(32, "removes explicit demographic cues"), (60.5, "reduces run-to-run noise"), (89, "defers remaining\nuncertainty at the margin")]:
    ax.text(x, 40.6, txt, ha="center", va="top", fontsize=9, color=BLUE, style="italic")
fig.savefig("figs/fig5_protocol.png", dpi=300, bbox_inches="tight", facecolor="white")
print("saved")
