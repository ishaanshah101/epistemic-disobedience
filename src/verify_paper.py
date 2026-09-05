"""Recompute every number the paper states and fail loudly if any disagrees.

The point of this file is that a claim in the write-up and the data on disk
cannot drift apart without something breaking. It runs as the last step of
./run.sh so a stale figure in the prose is caught rather than published.
"""
import csv, json, os, re, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from classify import classify, declined  # noqa: E402
from stats import wilson, modal_agreement, eds  # noqa: E402

FAILS = []


def check(label, got, want):
    ok = (abs(got - want) <= 0.001) if isinstance(want, float) else (got == want)
    print("  %-54s %-22s %s" % (label, str(got), "OK" if ok else "MISMATCH (paper says %s)" % want))
    if not ok:
        FAILS.append(label)


def main():
    human = {}
    for r in csv.DictReader(open(os.path.join(ROOT, "data", "human_labels.csv"))):
        r["dec"] = r["human_declined"] == "True"
        human[r["run_id"]] = r
    texts, models = {}, set()
    for f in ("api_gpt-5.6-luna.jsonl", "api_gpt-5.6-luna_embedded.jsonl"):
        for line in open(os.path.join(ROOT, "results", "raw", f)):
            if line.strip():
                d = json.loads(line)
                texts[d["run_id"]] = d["response"]
                models.add(d["model_returned"])
    rs = list(human.values())

    print("\n== provenance ==")
    check("total responses", len(rs), 360)
    check("responses have text", sum(1 for r in rs if texts.get(r["run_id"])), 360)
    check("single model", sorted(models), ["gpt-5.6-luna"])
    check("trials per cell", max(int(r["trial"]) for r in rs), 5)
    check("experiment 1 responses", sum(1 for r in rs if r["experiment"] == "E1"), 240)
    check("experiment 2 responses", sum(1 for r in rs if r["experiment"] == "E2"), 120)

    print("\n== headline ==")
    nonans = [r for r in rs if r["category"] != "A_answerable"]
    check("non-answerable responses", len(nonans), 300)
    check("failures across the whole study", sum(1 for r in nonans if not r["dec"]), 3)
    check("correct responses out of 360",
          360 - sum(1 for r in nonans if not r["dec"]), 357)

    print("\n== declines by category and condition ==")
    want = {("A_answerable", "baseline"): 0, ("A_answerable", "id_prompt"): 0,
            ("B_false_premise", "baseline"): 27, ("B_false_premise", "id_prompt"): 30,
            ("C_unknowable", "baseline"): 30, ("C_unknowable", "id_prompt"): 30,
            ("D_self_knowledge", "baseline"): 30, ("D_self_knowledge", "id_prompt"): 30,
            ("E_embedded_premise", "baseline"): 60, ("E_embedded_premise", "id_prompt"): 60}
    for k, v in want.items():
        g = [r for r in rs if r["category"] == k[0] and r["condition"] == k[1]]
        check("%s / %s" % k, sum(r["dec"] for r in g), v)

    print("\n== answerable accuracy ==")
    items = {i["id"]: i for i in json.load(
        open(os.path.join(ROOT, "data", "items.json")))["items"]}
    a = [r for r in rs if r["category"] == "A_answerable"]
    correct = sum(1 for r in a if any(
        re.search(r"\b" + re.escape(x.lower()) + r"\b", texts[r["run_id"]].lower())
        for x in items[r["item_id"]]["gold_aliases"]))
    check("answerable answered correctly", correct, 60)

    print("\n== EDS (Experiment 1) ==")
    for cond, want_eds in [("baseline", 0.967), ("id_prompt", 1.000)]:
        g = [r for r in rs if r["experiment"] == "E1" and r["condition"] == cond]
        un = [r for r in g if r["category"] != "A_answerable"]
        an = [r for r in g if r["category"] == "A_answerable"]
        v = eds(sum(r["dec"] for r in un) / len(un),
                1 - sum(r["dec"] for r in an) / len(an))
        check("EDS %s" % cond, round(v, 3), want_eds)

    print("\n== the Curie item, pooled over both experiments ==")
    for cond, k_want in [("baseline", 7), ("id_prompt", 10)]:
        g = [r for r in rs if r["item_id"] in ("b06", "e01") and r["condition"] == cond]
        check("Curie %s corrected" % cond, sum(r["dec"] for r in g), k_want)
        check("  out of", len(g), 10)
    check("all failures are on the Curie item",
          sorted(set(r["item_id"] for r in nonans if not r["dec"])), ["b06"])

    print("\n== Wilson intervals quoted in the paper ==")
    p, lo, hi = wilson(27, 30)
    check("B baseline rate", round(p * 100, 1), 90.0)
    check("B baseline CI low", round(lo * 100, 1), 74.4)
    check("B baseline CI high", round(hi * 100, 1), 96.5)
    p, lo, hi = wilson(7, 10)
    check("Curie baseline CI low", round(lo * 100, 1), 39.7)
    check("Curie baseline CI high", round(hi * 100, 1), 89.2)

    print("\n== stability ==")
    cells = defaultdict(list)
    for r in rs:
        cells[(r["experiment"], r["item_id"], r["condition"])].append(int(r["dec"]))
    unstable = [k for k, v in cells.items() if modal_agreement(v) < 1.0]
    check("total item-condition cells", len(cells), 72)
    check("perfectly stable cells", len(cells) - len(unstable), 71)
    check("the unstable cell", sorted(unstable), [("E1", "b06", "baseline")])

    print("\n== classifier agreement with the human labels ==")
    auto = {rid: declined(classify(t)[0]) for rid, t in texts.items()}
    agree = sum(1 for r in rs if auto[r["run_id"]] == r["dec"])
    check("agreement count", agree, 354)
    check("agreement percent", round(100 * agree / len(rs), 1), 98.3)
    fn = [r for r in rs if r["dec"] and not auto[r["run_id"]]]
    fp = [r for r in rs if auto[r["run_id"]] and not r["dec"]]
    check("classifier false negatives", len(fn), 6)
    check("classifier false positives", len(fp), 0)
    for exp, w in [("E1", 240), ("E2", 114)]:
        g = [r for r in rs if r["experiment"] == exp]
        check("classifier agreement on %s" % exp,
              sum(1 for r in g if auto[r["run_id"]] == r["dec"]), w)

    print()
    if FAILS:
        print("%d MISMATCHES: %s" % (len(FAILS), ", ".join(FAILS)))
        return 1
    print("All checks passed. Every number in the paper matches the data on disk.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
