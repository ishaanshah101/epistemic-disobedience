"""Draw a stratified sample for manual checking of the classifier.

The automatic labels are only worth what a human agreeing with them is worth,
so this pulls a fixed, seeded sample spread across categories and labels and
writes it to a CSV with an empty column to fill in by hand. Agreement between
the two columns is what gets reported in the paper.
"""
import argparse, os, sys
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="main")
    ap.add_argument("--per-cell", type=int, default=2)
    ap.add_argument("--seed", type=int, default=20260905)
    a = ap.parse_args()

    sys.path.insert(0, os.path.join(ROOT, "src"))
    from analyze import load
    df, _ = load(None)
    if df.empty:
        sys.exit("nothing to audit yet")

    sample = (df.groupby(["category", "label"], group_keys=False)
                .apply(lambda g: g.sample(min(len(g), a.per_cell),
                                          random_state=a.seed)))
    sample = sample[["run_id", "item_id", "category", "condition", "trial",
                     "label", "response"]].copy()
    sample["human_label"] = ""
    sample["agrees"] = ""
    out = os.path.join(ROOT, "results", "tables", "%s_audit_sample.csv" % a.tag)
    sample.to_csv(out, index=False)
    print("wrote %d rows to %s" % (len(sample), out))
    print("Fill in human_label with one of: challenge_premise, abstain, "
          "hedged_answer, answer")


if __name__ == "__main__":
    main()
