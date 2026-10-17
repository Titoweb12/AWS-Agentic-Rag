import json
import random
import sys
from collections import defaultdict

import anthropic
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()
claude = anthropic.Anthropic()
random.seed(42)

PER_SERVICE = 4
STYLES = [
    "in French, short and casual",
    "in English, as a concrete scenario ('I have ... how can I ...')",
    "in English, vague, from a beginner who does not know AWS vocabulary",
    "in French, precise",
]

chunks = [json.loads(l) for l in open("data/chunks.jsonl", encoding="utf-8")]
by_service = defaultdict(dict)
for c in chunks:
    if len(c["text"]) > 250:
        by_service[c["service"]].setdefault(c["question"], c)

rows = []
for service, questions in sorted(by_service.items()):
    for k, chunk in enumerate(random.sample(list(questions.values()), PER_SERVICE)):
        style = STYLES[k % len(STYLES)]
        msg = claude.messages.create(
            model="claude-haiku-5-5",
            max_tokens=1000,
            messages=[{"role": "user", "content": (
                "Here is an entry from an AWS FAQ.\n\n" + chunk["text"][:1500] +
                "\n\nWrite ONE question a user might ask whose answer is in this "
                "entry. Do not reuse the wording of the FAQ question; use everyday "
                f"words. Write it {style}. Reply with the question only."
            )}],
        )
        q = "".join(b.text for b in msg.content if b.type == "text").strip()
        rows.append({"question": q, "type": "answerable",
                     "service": service, "expected": [chunk["question"]]})
        print(f"{service}: {q}")

with open("eval/candidates.jsonl", "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(len(rows), "questions écrites dans eval/candidates.jsonl")