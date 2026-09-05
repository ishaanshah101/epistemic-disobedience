"""Fabrication recurrence analysis.

For false-premise items where the system asserted an answer instead of
challenging the premise, this asks whether it invented the *same* thing each
time. That distinction carries most of the practical weight of the study. A
fabrication that recurs identically across independent sessions is a stable
property of the model that can be located and fixed, whereas one that differs
every time leaves a user with no way to tell a good run from a bad one, since
the wrong answers do not even agree with each other.

Similarity is measured on content words with a Jaccard index. It is a crude
instrument and it is used only to rank items for human reading, never as a
finding on its own. The pairs it flags are printed in full so they can be
checked by eye.
"""
import json, os, re, sys, itertools
from collections import defaultdict

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from classify import classify, declined  # noqa: E402

STOP = set("""a an the and or but if then than that this these those of in on at to for with
from by as is are was were be been being it its it's you your i me my we our they them their
he she his her not no do does did doing have has had having will would can could should may
might must about into over under again further once here there when where why how all any both
each few more most other some such only own same so too very s t just don now""".split())

WORD = re.compile(r"[a-z0-9']+")


def content_words(text):
    return {w for w in WORD.findall((text or "").lower())
            if w not in STOP and len(w) > 2}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main():
    items = {i["id"]: i for i in
             json.load(open(os.path.join(ROOT, "data", "items.json")))["items"]}
    by_cell = defaultdict(list)
    for name in os.listdir(os.path.join(ROOT, "results", "raw")):
        if not name.endswith(".jsonl"):
            continue
        for line in open(os.path.join(ROOT, "results", "raw", name)):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("error"):
                continue
            label, _ = classify(r.get("response", ""))
            if declined(label):
                continue                      # only asserted answers are of interest
            it = items.get(r["item_id"])
            if not it or it["category"] != "B_false_premise":
                continue
            by_cell[(r["item_id"], r["condition"])].append(
                (r["run_id"], r.get("response", "")))

    rows = []
    for (item, cond), runs in sorted(by_cell.items()):
        if len(runs) < 2:
            continue
        sims = []
        for (ida, ta), (idb, tb) in itertools.combinations(runs, 2):
            sims.append(jaccard(content_words(ta), content_words(tb)))
        rows.append({
            "item_id": item, "condition": cond,
            "n_asserted": len(runs),
            "mean_pairwise_similarity": round(sum(sims) / len(sims), 4),
            "max_pairwise_similarity": round(max(sims), 4),
            "min_pairwise_similarity": round(min(sims), 4),
        })

    if not rows:
        print("No false-premise items were answered rather than challenged, so "
              "there is no fabrication to compare. That is itself a result.")
        return

    df = pd.DataFrame(rows).sort_values("mean_pairwise_similarity", ascending=False)
    out = os.path.join(ROOT, "results", "tables", "fabrication_recurrence.csv")
    df.to_csv(out, index=False)
    print(df.to_string(index=False))
    print("\nwrote", out)

    print("\n=== full text of the most similar cell, for human checking ===")
    top = df.iloc[0]
    for rid, txt in by_cell[(top["item_id"], top["condition"])]:
        print("\n--- %s ---\n%s" % (rid, txt[:700]))


if __name__ == "__main__":
    main()
