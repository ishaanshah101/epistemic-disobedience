"""Print the model IDs this API key can reach, so the study can be pinned to
a real model rather than a guessed name."""
import json, os, sys, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
key = os.environ.get("OPENAI_API_KEY") or open(os.path.join(ROOT, ".openai_key")).read().strip()
req = urllib.request.Request("https://api.openai.com/v1/models",
                             headers={"Authorization": "Bearer " + key})
d = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
ids = sorted(m["id"] for m in d.get("data", []))
chat = [i for i in ids if i.startswith(("gpt-", "o1", "o3", "o4", "chatgpt"))]
print("chat-capable models (%d):" % len(chat))
for i in chat:
    print("  ", i)
