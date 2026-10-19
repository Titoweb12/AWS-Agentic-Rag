import argparse
import contextlib
import io
import json
import pathlib
import re
import sys
import time
from collections import defaultdict

sys.path.insert(0, "src")
sys.stdout.reconfigure(encoding="utf-8")

import anthropic  # noqa: E402
import agent  # noqa: E402
import rag  # noqa: E402

JUDGE_MODEL = "claude-haiku-5-5"
judge_client = anthropic.Anthropic()


def load(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
def strip_sources(text):
    return re.split(r"\n\s*Sources\s*:", text)[0].strip()    


def found(row, passages):
    exp = [e.lower() for e in row["expected"]]
    if not exp:
        return None
    texts = [p["text"].lower() for p in passages]
    check = all if row.get("match") == "all" else any
    return check(any(e in t for t in texts) for e in exp)


def judge(question, passages, answer):
    ctx = "\n\n".join(f"[{p['id']}] {p['text'][:1200]}" for p in passages) or "(none)"
    prompt = (
        "You grade the answer of a question-answering system.\n"
        "You get a QUESTION, the PASSAGES the system was given, and its ANSWER.\n"
        'Reply with JSON only: {"refused": true|false, "unsupported": <integer>, '
        '"unsupported_claims": [<short quote of each unsupported claim>], '
        '"same_language": true|false}\n'
        "- refused: true if the answer declines to answer (says it does not know, "
        "that the question is out of scope, or that it is not covered). false if "
        "it gives substantive information.\n"
        "- unsupported: number of factual claims in the ANSWER that the PASSAGES "
        "do not support. Statements about the limits of the passages (for example "
        "'the excerpts do not say') are not factual claims. 0 if refused.\n"
        "- same_language: true if the ANSWER is written in the same language as "
        "the QUESTION.\n\n"
        f"QUESTION: {question}\n\nPASSAGES:\n{ctx}\n\nANSWER:\n{answer}"
    )
    msg = judge_client.messages.create(
        model=JUDGE_MODEL, max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = "".join(b.text for b in msg.content if b.type == "text")
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    return json.loads(m.group(0))


def run_naive(question):
    with contextlib.redirect_stdout(io.StringIO()):
        text, results = rag.answer(question)
    retrieved = [c for c, _ in results]
    skipped = text.startswith(("Cette question ne semble pas", "Je n'ai pas compris"))
    return {"answer": text, "retrieved": retrieved,
            "used": [] if skipped else retrieved, "reform": None}


def run_agent(question):
    with contextlib.redirect_stdout(io.StringIO()):
        s = agent.app.invoke({"question": question})
    retrieved = [c for c, _ in s.get("passages", [])]
    used = s.get("relevant", []) if s.get("sufficient") else []
    return {"answer": s["answer"], "retrieved": retrieved,
            "used": used, "reform": s.get("reformulations")}


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "-"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0, help="N premières questions de chaque jeu")
    args = ap.parse_args()

    sets = {"main": load("eval/questions.jsonl"), "multi": load("eval/multilingual.jsonl")}
    if args.limit:
        sets = {k: v[:args.limit] for k, v in sets.items()}
    systems = {"naif": run_naive, "agent": run_agent}

    out_dir = pathlib.Path("eval/results")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"run_{time.strftime('%Y%m%d_%H%M%S')}.jsonl"
    records = []

    with open(out_path, "w", encoding="utf-8") as f:
        for sname, fn in systems.items():
            for set_name, rows in sets.items():
                for i, row in enumerate(rows, 1):
                    for r in range(args.runs):
                        rec = {"system": sname, "set": set_name, "run": r,
                               "question": row["question"], "type": row["type"],
                               "lang": row.get("lang", "en")}
                        try:
                            o = fn(row["question"])
                            j = judge(row["question"], o["used"], strip_sources(o["answer"]))
                            rec.update(
                                hit5=found(row, o["retrieved"]),
                                hit_used=found(row, o["used"]),
                                refused=bool(j.get("refused")),
                                claims=j.get("unsupported_claims", []),
                                unsupported=int(j.get("unsupported", 0)),
                                same_language=bool(j.get("same_language")),
                                reform=o["reform"], answer=o["answer"],
                            )
                        except Exception as e:  # on garde la trace et on continue
                            rec["error"] = f"{type(e).__name__}: {e}"
                        records.append(rec)
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    print(f"[{sname}/{set_name}] {i}/{len(rows)}", flush=True)

    report(records)
    print("\nRésultats bruts :", out_path)


def report(records):
    for sname in ("naif", "agent"):
        mine = [r for r in records if r["system"] == sname]
        errors = [r for r in mine if "error" in r]
        ok = [r for r in mine if "error" not in r]
        print(f"\n===== {sname.upper()} ({len(errors)} erreurs) =====")

        ans = [r for r in ok if r["set"] == "main" and r["type"] == "answerable"]
        given = [r for r in ans if not r["refused"]]
        print(f"Questions à réponse ({len(ans)} essais)")
        print("  hit@5            ", pct(sum(bool(r["hit5"]) for r in ans), len(ans)))
        print("  hit utilisé      ", pct(sum(bool(r["hit_used"]) for r in ans), len(ans)))
        print("  réponse donnée   ", pct(len(given), len(ans)))
        print("  fidélité         ", pct(sum(r["unsupported"] == 0 for r in given), len(given)))
        print("  langue correcte  ", pct(sum(r["same_language"] for r in given), len(given)))
        refs = [r["reform"] for r in ans if r["reform"] is not None]
        if refs:
            print("  reformulations   ", f"{sum(refs) / len(refs):.2f} en moyenne")

        no = [r for r in ok if r["set"] == "main" and r["type"] != "answerable"]
        print(f"Refus attendus ({len(no)} essais) :", pct(sum(r["refused"] for r in no), len(no)))

        print("Multilingue (hit@5 / langue correcte)")
        for lang in ("fr", "it", "de"):
            ml = [r for r in ok if r["set"] == "multi" and r["lang"] == lang]
            g = [r for r in ml if not r["refused"]]
            print(f"  {lang}: {pct(sum(bool(r['hit5']) for r in ml), len(ml))} / "
                  f"{pct(sum(r['same_language'] for r in g), len(g))}")

        fails = defaultdict(int)
        for r in ans:
            if not r["hit_used"] or r["refused"] or r["unsupported"] > 0:
                fails[r["question"]] += 1
        if fails:
            print("Questions les plus ratées :")
            for q, n in sorted(fails.items(), key=lambda x: -x[1])[:5]:
                print(f"  {n}x  {q[:90]}")


if __name__ == "__main__":
    main()