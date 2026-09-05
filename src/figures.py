"""Build the paper figures from the human labels.

The two-slot categorical pair is blue #2a78d6 and orange #eb6834, checked with a
colorblind-separation validator rather than picked by eye (worst adjacent CVD
delta-E 24.7, normal-vision 33.6, both clear of the floors). Every bar carries a
direct value label, so magnitude survives printing in black and white and
identity never rests on color alone.
"""
import csv, json, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from stats import wilson  # noqa: E402

TAB = os.path.join(ROOT, "results", "tables")
FIG = os.path.join(ROOT, "results", "figures")

C_BASE, C_ID, C_GREY = "#2a78d6", "#eb6834", "#8a8a85"
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e3e2df", "#fcfcfb"
CONDLAB = {"baseline": "Baseline", "id_prompt": "Five-step prompt"}
GROUPS = [
    ("A_answerable",       "A. Answerable\n(should answer)"),
    ("B_false_premise",    "B. False premise\n(should challenge)"),
    ("C_unknowable",       "C. Unknowable\n(should decline)"),
    ("D_self_knowledge",   "D. Self-knowledge\n(should decline)"),
    ("E_embedded_premise", "E. Embedded premise\n(should correct)"),
]


def style(ax):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(GRID)
    ax.tick_params(colors=MUTED, length=0)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.xaxis.grid(False)


def rows():
    return list(csv.DictReader(open(os.path.join(ROOT, "data", "human_labels.csv"))))


def fig_rates():
    rs = rows()
    fig, ax = plt.subplots(figsize=(9.6, 4.7))
    w = 0.38
    for i, cond in enumerate(["baseline", "id_prompt"]):
        xs, ys, his = [], [], []
        for j, (cat, _) in enumerate(GROUPS):
            g = [r for r in rs if r["category"] == cat and r["condition"] == cond]
            k = sum(r["human_declined"] == "True" for r in g)
            p, lo, hi = wilson(k, len(g))
            # Wilson can return an upper bound a hair below p at p=1, so clamp.
            xs.append(j + (i - 0.5) * w); ys.append(p * 100)
            his.append(max(0.0, (hi - p) * 100))
        ax.bar(xs, ys, width=w * 0.92, color=C_BASE if i == 0 else C_ID,
               label=CONDLAB[cond], zorder=3, edgecolor=SURFACE, linewidth=2)
        ax.errorbar(xs, ys, yerr=[[0] * len(ys), his], fmt="none", ecolor=MUTED,
                    elinewidth=1.4, capsize=3, zorder=4)
        for x, y, h in zip(xs, ys, his):
            ax.text(x, y + h + 2.5, "%.0f" % y, ha="center", va="bottom",
                    fontsize=9.5, color=INK, zorder=5)
    ax.set_xticks(range(len(GROUPS)))
    ax.set_xticklabels([l for _, l in GROUPS], fontsize=9, color=MUTED)
    ax.set_ylabel("Responses that withheld or corrected (%)", fontsize=10, color=MUTED)
    ax.set_ylim(0, 118); ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_title("Epistemic behavior by question type, scored by hand",
                 fontsize=13, color=INK, pad=16, loc="left")
    style(ax)
    ax.legend(frameon=False, fontsize=9.5, labelcolor=MUTED, loc="upper left",
              bbox_to_anchor=(0.0, 1.03), ncol=2)
    fig.tight_layout()
    out = os.path.join(FIG, "fig1_rates_by_type.png")
    fig.savefig(out, dpi=220); fig.savefig(out.replace(".png", ".pdf"))
    plt.close(fig); return out


def fig_scorer_gap():
    """The measured failure rate depended almost entirely on who did the scoring."""
    labels = ["Rule-based\nscorer, v1", "Rule-based\nscorer, v2", "Read by hand\n(ground truth)"]
    vals = [48.3, 91.7, 100.0]
    colors = [C_GREY, C_GREY, C_BASE]
    fig, ax = plt.subplots(figsize=(7.4, 4.3))
    ax.bar(range(3), vals, width=0.5, color=colors, zorder=3,
           edgecolor=SURFACE, linewidth=2)
    for x, v in zip(range(3), vals):
        ax.text(x, v + 2.5, "%.1f%%" % v, ha="center", va="bottom",
                fontsize=11, color=INK, zorder=5)
    ax.axhline(100, color=MUTED, linestyle=":", linewidth=1.2, zorder=2)
    ax.set_xticks(range(3)); ax.set_xticklabels(labels, fontsize=9.5, color=MUTED)
    ax.set_ylabel("Measured correction rate,\nExperiment 2 baseline (%)",
                  fontsize=10, color=MUTED)
    ax.set_ylim(0, 118); ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_title("The same 60 responses, scored three ways",
                 fontsize=13, color=INK, pad=16, loc="left")
    style(ax)
    fig.tight_layout()
    out = os.path.join(FIG, "fig2_scorer_gap.png")
    fig.savefig(out, dpi=220); fig.savefig(out.replace(".png", ".pdf"))
    plt.close(fig); return out


def fig_curie():
    """The only item in the study the model ever got wrong."""
    rs = [r for r in rows() if r["item_id"] in ("b06", "e01")]
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    xs, ys, his = [], [], []
    for i, cond in enumerate(["baseline", "id_prompt"]):
        g = [r for r in rs if r["condition"] == cond]
        k = sum(r["human_declined"] == "True" for r in g)
        p, lo, hi = wilson(k, len(g))
        xs.append(i); ys.append(p * 100)
        his.append([max(0.0, (p - lo) * 100), max(0.0, (hi - p) * 100)])
    ax.bar(xs, ys, width=0.45, color=[C_BASE, C_ID], zorder=3,
           edgecolor=SURFACE, linewidth=2)
    ax.errorbar(xs, ys, yerr=list(zip(*his)), fmt="none", ecolor=MUTED,
                elinewidth=1.4, capsize=4, zorder=4)
    for x, y, h in zip(xs, ys, his):
        ax.text(x, y + h[1] + 2.5, "%.0f%%" % y, ha="center", va="bottom",
                fontsize=11, color=INK, zorder=5)
    ax.set_xticks(xs); ax.set_xticklabels(["Baseline", "Five-step prompt"],
                                          fontsize=10, color=MUTED)
    ax.set_ylabel("Runs that corrected\nthe premise (%)", fontsize=10, color=MUTED)
    ax.set_ylim(0, 128); ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_title("The Curie item, ten independent runs per condition\n"
                 "the only question in the study the model ever got wrong",
                 fontsize=11.5, color=INK, pad=12, loc="left")
    style(ax)
    fig.tight_layout()
    out = os.path.join(FIG, "fig3_curie_item.png")
    fig.savefig(out, dpi=220); fig.savefig(out.replace(".png", ".pdf"))
    plt.close(fig); return out


if __name__ == "__main__":
    os.makedirs(FIG, exist_ok=True)
    for fn in (fig_rates, fig_scorer_gap, fig_curie):
        try:
            print("wrote", fn())
        except Exception as e:  # noqa: BLE001
            print("FAILED %s: %r" % (fn.__name__, e))
