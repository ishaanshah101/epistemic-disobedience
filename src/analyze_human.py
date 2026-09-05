"""Primary analysis, scored against the human labels.

All 360 responses were read and labelled by hand. Those labels are the ground
truth reported in the paper. The rule-based classifier is retained and its
agreement with the human labels is reported, because the size of that gap turned
out to be one of the more useful things this study found.
"""
import csv, json, os, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from classify import classify, declined  # noqa: E402
from stats import wilson, modal_agreement, eds, bootstrap_ci  # noqa: E402

CATS = ["A_answerable", "B_false_premise", "C_unknowable",
        "D_self_knowledge", "E_embedded_premise"]


def load():
    human = {}
    for r in csv.DictReader(open(os.path.join(ROOT, "data", "human_labels.csv"))):
        r["human_declined"] = r["human_declined"] == "True"
        r["trial"] = int(r["trial"])
        human[r["run_id"]] = r
    texts = {}
    for f in ("api_gpt-5.6-luna.jsonl", "api_gpt-5.6-luna_embedded.jsonl"):
        for line in open(os.path.join(ROOT, "results", "raw", f)):
            if line.strip():
                d = json.loads(line)
                texts[d["run_id"]] = d["response"]
    rows = []
    for rid, h in human.items():
        lab, _ = classify(texts[rid])
        rows.append({**h, "auto_label": lab, "auto_declined": declined(lab),
                     "response": texts[rid]})
    return rows


def main():
    rows = load()
    tab = os.path.join(ROOT, "results", "tables")
    os.makedirs(tab, exist_ok=True)

    with open(os.path.join(tab, "human_scored.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[k for k in rows[0] if k != "response"])
        w.writeheader()
        for r in rows:
            w.writerow({k: v for k, v in r.items() if k != "response"})

    print("=== BEHAVIOR BY CATEGORY (human labels) ===")
    print("%-20s %-10s %6s %8s %9s %s" % ("category", "condition", "n", "declined", "rate", "95% CI"))
    out = []
    for cat in CATS:
        for cond in ("baseline", "id_prompt"):
            g = [r for r in rows if r["category"] == cat and r["condition"] == cond]
            if not g:
                continue
            k = sum(r["human_declined"] for r in g)
            p, lo, hi = wilson(k, len(g))
            out.append({"category": cat, "condition": cond, "n": len(g), "declined": k,
                        "rate": round(p, 4), "ci_low": round(lo, 4), "ci_high": round(hi, 4)})
            print("%-20s %-10s %6d %8d %8.3f  [%.3f, %.3f]" % (cat, cond, len(g), k, p, lo, hi))
    with open(os.path.join(tab, "human_rates.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)

    print("\n=== EDS (Experiment 1 categories only) ===")
    for cond in ("baseline", "id_prompt"):
        g = [r for r in rows if r["experiment"] == "E1" and r["condition"] == cond]
        un = [r for r in g if r["category"] != "A_answerable"]
        an = [r for r in g if r["category"] == "A_answerable"]
        dr = sum(r["human_declined"] for r in un) / len(un)
        ar = 1 - sum(r["human_declined"] for r in an) / len(an)
        print("  %-10s decline(unanswerable)=%.4f answer(answerable)=%.4f  EDS=%.4f"
              % (cond, dr, ar, eds(dr, ar)))

    print("\n=== EVERY RESPONSE THE HUMAN READING SCORES AS A FAILURE ===")
    fails = [r for r in rows if r["category"] != "A_answerable" and not r["human_declined"]]
    for r in sorted(fails, key=lambda r: r["run_id"]):
        print("  %-24s %s" % (r["run_id"], r["note"]))
    print("  total failures: %d out of %d non-answerable responses"
          % (len(fails), sum(1 for r in rows if r["category"] != "A_answerable")))

    print("\n=== STABILITY (human labels) ===")
    cells = defaultdict(list)
    for r in rows:
        cells[(r["experiment"], r["item_id"], r["condition"])].append(int(r["human_declined"]))
    unstable = [k for k, v in cells.items() if modal_agreement(v) < 1.0]
    print("  perfectly stable cells: %d/%d" % (len(cells) - len(unstable), len(cells)))
    print("  unstable cells: %s" % (unstable or "none"))

    print("\n=== THE CURIE ITEM, POOLED ACROSS BOTH EXPERIMENTS (identical prompt) ===")
    for cond in ("baseline", "id_prompt"):
        g = [r for r in rows if r["item_id"] in ("b06", "e01") and r["condition"] == cond]
        k = sum(r["human_declined"] for r in g)
        p, lo, hi = wilson(k, len(g))
        print("  %-10s corrected %d/%d = %.2f  [%.3f, %.3f]" % (cond, k, len(g), p, lo, hi))

    print("\n=== CLASSIFIER AGREEMENT WITH THE HUMAN LABELS ===")
    agree = sum(1 for r in rows if r["auto_declined"] == r["human_declined"])
    print("  overall: %d/%d = %.1f%%" % (agree, len(rows), 100 * agree / len(rows)))
    for exp in ("E1", "E2"):
        g = [r for r in rows if r["experiment"] == exp]
        a = sum(1 for r in g if r["auto_declined"] == r["human_declined"])
        print("  %s: %d/%d = %.1f%%" % (exp, a, len(g), 100 * a / len(g)))
    fn = [r for r in rows if r["human_declined"] and not r["auto_declined"]]
    fp = [r for r in rows if r["auto_declined"] and not r["human_declined"]]
    print("  classifier missed a real decline (false negative): %d" % len(fn))
    print("  classifier invented a decline (false positive):    %d" % len(fp))
    print("  the misses:", sorted(r["run_id"] for r in fn))

    summary = {
        "n": len(rows), "failures": len(fails),
        "failure_run_ids": sorted(r["run_id"] for r in fails),
        "classifier_agreement": round(agree / len(rows), 4),
        "classifier_false_negatives": len(fn), "classifier_false_positives": len(fp),
        "unstable_cells": [list(k) for k in unstable],
    }
    json.dump(summary, open(os.path.join(tab, "human_summary.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
