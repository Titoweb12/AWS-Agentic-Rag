import glob
import json
from collections import defaultdict

path = sorted(glob.glob("eval/results/run_*.jsonl"))[-1]
rows = [json.loads(l) for l in open(path, encoding="utf-8")]
print("Fichier :", path)

for system in ("naif", "agent"):
    cats = defaultdict(list)
    for r in rows:
        if r["system"] != system or r["set"] != "main" or r["type"] != "answerable" or "error" in r:
            continue
        if r["refused"] and r["reform"] is None and system == "agent":
            cats["refus du routeur"].append(r)
        elif r["refused"]:
            cats["refus après recherche"].append(r)
        elif not r["hit_used"]:
            cats["répond sans le bon passage"].append(r)
        elif r["unsupported"] > 0:
            cats["affirmation non soutenue"].append(r)
        if not r["refused"] and not r["same_language"]:
            cats["mauvaise langue"].append(r)
    print(f"\n===== {system.upper()} =====")
    for cat, items in cats.items():
        print(f"{cat} : {len(items)}")
        for r in items[:8]:
            print("   -", r["question"][:95])
            for cl in r.get("claims", [])[:3]:
                print("       ·", str(cl)[:110])            