"""Collect responses from the OpenAI API.

Design notes that matter for the results rather than for the code:

Every trial is an independent request with no conversation history. That is
the property the consistency analysis depends on, because if trials shared a
context the model would simply be agreeing with itself, and stability would be
an artefact of the setup rather than a fact about the model.

Temperature is left at the API default rather than pinned to zero. Zero would
make the model close to deterministic and would answer a question nobody
asked, since the deployed product users actually talk to does not run at zero.
The point of repeating trials is to measure the variability a real user is
exposed to.

Runs are keyed by run_id and appended to a JSONL file. Re-running skips work
already on disk, so an interrupted collection resumes instead of restarting.
"""
import argparse, json, os, sys, time, random
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from conditions import CONDITIONS  # noqa: E402

API_URL = "https://api.openai.com/v1/chat/completions"


def load_key():
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        path = os.path.join(ROOT, ".openai_key")
        if os.path.exists(path):
            key = open(path).read().strip()
    if not key:
        sys.exit("No API key. Set OPENAI_API_KEY or write it to .openai_key "
                 "(which is gitignored).")
    return key


def call(prompt, model, key, max_retries=5, timeout=90):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        API_URL, data=body,
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json"})
    last = None
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.loads(r.read().decode())
            return {
                "response": d["choices"][0]["message"]["content"],
                "model_returned": d.get("model"),
                "finish_reason": d["choices"][0].get("finish_reason"),
                "usage": d.get("usage", {}),
                "error": None,
            }
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:300]
            last = "HTTP %s: %s" % (e.code, detail)
            # 400-class errors other than rate limiting will not fix themselves.
            if e.code not in (429, 500, 502, 503, 504):
                break
        except Exception as e:  # noqa: BLE001
            last = repr(e)
        time.sleep((2 ** attempt) + random.random())
    return {"response": "", "model_returned": None, "finish_reason": None,
            "usage": {}, "error": last}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default=None)
    ap.add_argument("--items", default="items.json",
                    help="which item file in data/ to run")
    ap.add_argument("--limit", type=int, default=None,
                    help="stop after N new calls, for a cheap smoke test")
    a = ap.parse_args()

    key = load_key()
    items = json.load(open(os.path.join(ROOT, "data", a.items)))["items"]
    stem = a.items.replace("items", "").replace(".json", "").strip("_-") or "main"
    out = a.out or os.path.join(ROOT, "results", "raw",
                                "api_%s_%s.jsonl" % (a.model.replace("/", "_"), stem))
    os.makedirs(os.path.dirname(out), exist_ok=True)

    done = set()
    if os.path.exists(out):
        for line in open(out):
            try:
                done.add(json.loads(line)["run_id"])
            except Exception:
                pass

    jobs = []
    for it in items:
        for cond, wrap in CONDITIONS.items():
            for t in range(1, a.trials + 1):
                rid = "%s__%s__t%d" % (it["id"], cond, t)
                if rid in done:
                    continue
                jobs.append((rid, it, cond, t, wrap(it["prompt"])))
    random.Random(20260905).shuffle(jobs)
    if a.limit:
        jobs = jobs[:a.limit]

    print("%d already on disk, %d to collect -> %s" % (len(done), len(jobs), out))
    if not jobs:
        return

    lock_file = open(out, "a")
    n_err = 0

    def work(job):
        rid, it, cond, t, prompt = job
        r = call(prompt, a.model, key)
        return {
            "run_id": rid, "item_id": it["id"], "category": it["category"],
            "condition": cond, "trial": t, "prompt_sent": prompt,
            "response": r["response"], "model_requested": a.model,
            "model_returned": r["model_returned"],
            "finish_reason": r["finish_reason"], "usage": r["usage"],
            "error": r["error"], "searched": False,
            "source": "openai_api", "collected_at": time.time(),
        }

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(work, j): j for j in jobs}
        for i, f in enumerate(as_completed(futs), 1):
            rec = f.result()
            if rec["error"]:
                n_err += 1
            lock_file.write(json.dumps(rec) + "\n")
            lock_file.flush()
            if i % 10 == 0 or i == len(jobs):
                print("  %d/%d done (%d errors)" % (i, len(jobs), n_err))
    lock_file.close()
    print("finished. errors: %d" % n_err)


if __name__ == "__main__":
    main()
