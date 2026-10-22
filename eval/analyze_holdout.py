import glob
import json

path = sorted(glob.glob("eval/results/run_*.jsonl"))[-1]
print("Fichier :", path)
hold = {}
for l in open("eval/holdout.jsonl", encoding="utf-8"):
    if l.strip():
        h = json.loads(l)
        hold[h["question"]] = h
rows = [json.loads(l) for l in open(path, encoding="utf-8")]


def kind(r):
    h = hold.get(r["question"], {})
    if h.get("type") != "answerable":
        return None
    return "deux services" if h.get("match") == "all" else "simple"


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "-"


for system in ("naif", "naif_strict", "agent"):
    print(f"\n===== {system} =====")
    for k in ("simple", "deux services"):
        rs = [r for r in rows if r["system"] == system and "error" not in r and kind(r) == k]
        given = [r for r in rs if not r["refused"]]
        print(
            f"{k} ({len(rs)} essais) : "
            f"hit utilisé {pct(sum(bool(r['hit_used']) for r in rs), len(rs))} | "
            f"réponse donnée {pct(len(given), len(rs))} | "
            f"fidélité {pct(sum(r['unsupported'] == 0 for r in given), len(given))}"
        )