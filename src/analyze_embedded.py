"""Score Experiment 2, the embedded-false-premise set.

Experiment 1 put the model at ceiling on blatantly unanswerable questions and
left exactly one item failing, the one where the false detail sat inside an
otherwise true statement. Experiment 2 exists so that observation is tested on
a set built for it rather than rested on a single data point.
"""
import json, os, sys
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from classify import classify, declined  # noqa: E402
from stats import wilson, bootstrap_ci, modal_agreement, mcnemar_exact  # noqa: E402

RAW = os.path.join(ROOT, "results", "raw", "api_gpt-5.6-luna_embedded.jsonl")
TAB = os.path.join(ROOT, "results", "tables")


def main():
    items = {i["id"]: i for i in
             json.load(open(os.path.join(ROOT, "data", "items_embedded.json")))["items"]}
    rows = []
    for line in open(RAW):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if r.get("error"):
            continue
        lab, _ = classify(r["response"])
        rows.append({"run_id": r["run_id"], "item_id": r["item_id"],
                     "condition": r["condition"], "trial": r["trial"],
                     "label": lab, "declined": declined(lab),
                     "model_returned": r.get("model_returned"),
                     "response": r["response"]})
    df = pd.DataFrame(rows)
    os.makedirs(TAB, exist_ok=True)
    df.drop(columns=["response"]).to_csv(
        os.path.join(TAB, "embedded_scored.csv"), index=False)

    out = []
    for cond, g in df.groupby("condition"):
        k, n = int(g["declined"].sum()), len(g)
        p, lo, hi = wilson(k, n)
        out.append({"condition": cond, "n": n, "corrected": k,
                    "correction_rate": round(p, 4),
                    "ci_low": round(lo, 4), "ci_high": round(hi, 4)})
    rates = pd.DataFrame(out)
    rates.to_csv(os.path.join(TAB, "embedded_rates.csv"), index=False)

    piv = df.groupby(["item_id", "condition"])["declined"].mean().unstack()
    d, lo, hi = bootstrap_ci(list(piv["id_prompt"] - piv["baseline"]))
    b = int(((piv["baseline"] <= .5) & (piv["id_prompt"] > .5)).sum())
    c = int(((piv["id_prompt"] <= .5) & (piv["baseline"] > .5)).sum())

    stab = []
    for (item, cond), g in df.groupby(["item_id", "condition"]):
        stab.append({"item_id": item, "condition": cond,
                     "decision_agreement": round(modal_agreement(list(g["declined"].astype(int))), 4),
                     "labels": "|".join(g.sort_values("trial")["label"])})
    st = pd.DataFrame(stab)
    st["unstable"] = st["decision_agreement"] < 1.0
    st.to_csv(os.path.join(TAB, "embedded_stability.csv"), index=False)

    summary = {
        "n_responses": int(len(df)), "n_items": int(df["item_id"].nunique()),
        "models_returned": sorted(df["model_returned"].dropna().unique().tolist()),
        "rates": out,
        "paired_diff": round(d, 4), "diff_ci": [round(lo, 4), round(hi, 4)],
        "mcnemar_exact_p": round(mcnemar_exact(b, c), 5),
        "perfectly_stable": int((~st["unstable"]).sum()),
        "total_item_conditions": int(len(st)),
        "stable_by_condition": {c_: int((~st[st["condition"] == c_]["unstable"]).sum())
                                for c_ in st["condition"].unique()},
        "per_item": {i: {"baseline": float(piv.loc[i, "baseline"]),
                         "id_prompt": float(piv.loc[i, "id_prompt"])} for i in piv.index},
    }
    json.dump(summary, open(os.path.join(TAB, "embedded_summary.json"), "w"), indent=2)
    print(rates.to_string(index=False))
    print("\npaired diff %.4f  95%% CI [%.4f, %.4f]  McNemar p=%.4f" % (d, lo, hi, summary["mcnemar_exact_p"]))
    print("stable: %d/%d" % (summary["perfectly_stable"], summary["total_item_conditions"]))
    print("\nunstable cells:")
    print(st[st["unstable"]].to_string(index=False))


if __name__ == "__main__":
    main()
