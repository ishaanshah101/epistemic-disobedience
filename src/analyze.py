"""Score the collected responses and write the tables the paper reports.

Reads every JSONL file in results/raw, applies the frozen classifier, and
writes tidy CSVs plus a summary JSON. Nothing here touches the network, so the
analysis can be re-run and audited without re-collecting anything.
"""
import argparse, glob, json, os, sys
from collections import defaultdict

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from classify import classify, declined, is_correct_answer  # noqa: E402
from stats import wilson, mcnemar_exact, eds, modal_agreement, bootstrap_ci  # noqa: E402

CATS = ["A_answerable", "B_false_premise", "C_unknowable", "D_self_knowledge"]
UNANSWERABLE = CATS[1:]


def load(sources=None):
    items = {i["id"]: i for i in
             json.load(open(os.path.join(ROOT, "data", "items.json")))["items"]}
    rows = []
    for path in sorted(glob.glob(os.path.join(ROOT, "results", "raw", "*.jsonl"))):
        for line in open(path):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("error"):
                continue
            if sources and r.get("source") not in sources:
                continue
            it = items.get(r["item_id"])
            if not it:
                continue
            label, ev = classify(r.get("response", ""))
            rows.append({
                "run_id": r["run_id"], "item_id": r["item_id"],
                "category": it["category"], "condition": r["condition"],
                "trial": r["trial"], "source": r.get("source", "unknown"),
                "model_returned": r.get("model_returned"),
                "label": label, "declined": declined(label),
                "searched": bool(r.get("searched", False)),
                "chars": len(r.get("response", "")),
                "correct": is_correct_answer(r.get("response", ""),
                                             it.get("gold_aliases") or []),
                "response": r.get("response", ""),
            })
    return pd.DataFrame(rows), items


def rate_table(df):
    out = []
    for (cat, cond), g in df.groupby(["category", "condition"]):
        k = int(g["declined"].sum()); n = len(g)
        p, lo, hi = wilson(k, n)
        out.append({"category": cat, "condition": cond, "n": n,
                    "declined": k, "decline_rate": round(p, 4),
                    "ci_low": round(lo, 4), "ci_high": round(hi, 4),
                    "search_rate": round(g["searched"].mean(), 4)})
    return pd.DataFrame(out).sort_values(["category", "condition"])


def eds_table(df):
    out = []
    for cond, g in df.groupby("condition"):
        un = g[g["category"].isin(UNANSWERABLE)]
        an = g[g["category"] == "A_answerable"]
        if len(un) == 0 or len(an) == 0:
            continue
        dr = un["declined"].mean()
        ar = 1 - an["declined"].mean()
        out.append({"condition": cond, "n_unanswerable": len(un),
                    "n_answerable": len(an),
                    "decline_rate_unanswerable": round(dr, 4),
                    "answer_rate_answerable": round(ar, 4),
                    "EDS": round(eds(dr, ar), 4)})
    return pd.DataFrame(out)


def stability_table(df):
    out = []
    for (item, cond), g in df.groupby(["item_id", "condition"]):
        labels = list(g["label"])
        dec = list(g["declined"].astype(int))
        out.append({
            "item_id": item, "condition": cond, "n_trials": len(g),
            "category": g["category"].iloc[0],
            "label_agreement": round(modal_agreement(labels), 4),
            "decision_agreement": round(modal_agreement(dec), 4),
            "unstable": modal_agreement(dec) < 1.0,
            "labels": "|".join(labels),
        })
    return pd.DataFrame(out).sort_values(["category", "item_id", "condition"])


def condition_test(df):
    """Exact McNemar on item-level decline decisions, paired across conditions."""
    piv = (df.groupby(["item_id", "condition"])["declined"].mean().unstack())
    if piv.shape[1] < 2 or "baseline" not in piv or "id_prompt" not in piv:
        return {"note": "both conditions required for the paired test"}
    base = (piv["baseline"] > 0.5).astype(int)
    idp = (piv["id_prompt"] > 0.5).astype(int)
    b = int(((base == 0) & (idp == 1)).sum())   # gained a decline
    c = int(((base == 1) & (idp == 0)).sum())   # lost a decline
    diff, lo, hi = bootstrap_ci(list(piv["id_prompt"] - piv["baseline"]))
    return {"n_items": int(len(piv)), "baseline_to_decline": b,
            "decline_to_baseline": c, "mcnemar_exact_p": round(mcnemar_exact(b, c), 5),
            "mean_paired_diff": round(diff, 4),
            "diff_ci_low": round(lo, 4), "diff_ci_high": round(hi, 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", nargs="*", default=None)
    ap.add_argument("--tag", default="main")
    a = ap.parse_args()

    df, items = load(a.sources)
    if df.empty:
        sys.exit("No usable rows found in results/raw/")

    tdir = os.path.join(ROOT, "results", "tables")
    os.makedirs(tdir, exist_ok=True)
    df.drop(columns=["response"]).to_csv(
        os.path.join(tdir, "%s_scored.csv" % a.tag), index=False)

    rates = rate_table(df); rates.to_csv(os.path.join(tdir, "%s_rates.csv" % a.tag), index=False)
    edst = eds_table(df); edst.to_csv(os.path.join(tdir, "%s_eds.csv" % a.tag), index=False)
    stab = stability_table(df); stab.to_csv(os.path.join(tdir, "%s_stability.csv" % a.tag), index=False)
    test = condition_test(df)

    acc = df[(df["category"] == "A_answerable") & (~df["declined"])]
    summary = {
        "tag": a.tag,
        "n_responses": int(len(df)),
        "n_items": int(df["item_id"].nunique()),
        "sources": sorted(df["source"].unique().tolist()),
        "models_returned": sorted([m for m in df["model_returned"].dropna().unique().tolist()]),
        "trials_per_cell": int(df.groupby(["item_id", "condition"]).size().max()),
        "overall_decline_rate": round(float(df["declined"].mean()), 4),
        "overall_search_rate": round(float(df["searched"].mean()), 4),
        "answerable_accuracy_when_answered": (
            round(float(acc["correct"].mean()), 4) if len(acc) and acc["correct"].notna().any() else None),
        "unstable_item_conditions": int(stab["unstable"].sum()),
        "total_item_conditions": int(len(stab)),
        "condition_test": test,
        "label_counts": df["label"].value_counts().to_dict(),
    }
    json.dump(summary, open(os.path.join(tdir, "%s_summary.json" % a.tag), "w"), indent=2)

    print("\n=== DECLINE RATES ==="); print(rates.to_string(index=False))
    print("\n=== EDS ==="); print(edst.to_string(index=False))
    print("\n=== STABILITY (unstable only) ===")
    u = stab[stab["unstable"]]
    print(u.to_string(index=False) if len(u) else "  every item was perfectly stable")
    print("\n=== SUMMARY ==="); print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
