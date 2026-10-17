import json

chunks = [json.loads(l)["text"].lower() for l in open("data/chunks.jsonl", encoding="utf-8")]
bad = n = 0
for path in ["eval/questions.jsonl", "eval/multilingual.jsonl"]:
    for i, line in enumerate(open(path, encoding="utf-8"), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        n += 1
        for e in row["expected"]:
            if not any(e.lower() in c for c in chunks):
                bad += 1
                print(path, "ligne", i, "introuvable :", e)
print(n, "questions,", bad, "passages attendus introuvables")