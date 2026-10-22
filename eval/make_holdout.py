import json
import random
import sys
from collections import defaultdict

import anthropic
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()
claude = anthropic.Anthropic()
random.seed(7)

chunks = [json.loads(l) for l in open("data/chunks.jsonl", encoding="utf-8")]

used = set()
for path in ["eval/questions.jsonl", "eval/multilingual.jsonl", "eval/candidates.jsonl"]:
    for line in open(path, encoding="utf-8"):
        if line.strip():
            used.update(e.lower() for e in json.loads(line)["expected"])

unique = {}
for c in chunks:
    q = c["question"]
    if len(c["text"]) <= 250 or any(u in q.lower() for u in used):
        continue
    unique.setdefault(q, c)

by_service = defaultdict(list)
for c in unique.values():
    by_service[c["service"]].append(c)
for s in by_service:
    random.shuffle(by_service[s])
services = sorted(by_service)

picked, i = [], 0
while len(picked) < 16:
    s = services[i % len(services)]
    if by_service[s]:
        picked.append(by_service[s].pop())
    i += 1

order = services[:]
random.shuffle(order)
pairs = [(by_service[order[2 * k]].pop(), by_service[order[2 * k + 1]].pop()) for k in range(4)]

STYLES = [
    "in English, as a concrete scenario ('I have ... how can I ...')",
    "in English, short and casual, with a typo or two",
    "in English, vague, from a beginner who does not know AWS vocabulary",
    "in English, precise and technical",
]


def ask(prompt):
    msg = claude.messages.create(
        model="claude-haiku-5-5", max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if b.type == "text").strip()


rows = []
for k, c in enumerate(picked):
    q = ask(
        "Here is an entry from an AWS FAQ.\n\n" + c["text"][:1500] +
        "\n\nWrite ONE question a user might ask whose answer is in this entry. "
        "Do not reuse the wording of the FAQ question; use everyday words. "
        f"Write it {STYLES[k % len(STYLES)]}. Reply with the question only."
    )
    rows.append({"question": q, "type": "answerable", "service": c["service"],
                 "expected": [c["question"]]})
    print(f"{c['service']}: {q}")

for a, b in pairs:
    q = ask(
        "Here are two entries from the FAQs of two different AWS services.\n\n"
        f"ENTRY 1 ({a['service']}):\n{a['text'][:1200]}\n\n"
        f"ENTRY 2 ({b['service']}):\n{b['text'][:1200]}\n\n"
        "Write ONE realistic question from a user whose situation needs "
        "information from BOTH entries to be answered fully. Use everyday words, "
        "in English. Reply with the question only."
    )
    rows.append({"question": q, "type": "answerable",
                 "expected": [a["question"], b["question"]], "match": "all"})
    print(f"{a['service']} + {b['service']}: {q}")

rows.append({"question": "What is the capital of Australia?", "type": "off_topic", "expected": []})
rows.append({"question": "How do I set up lifecycle rules in Google Cloud Storage?",
             "type": "off_topic", "expected": []})

with open("eval/holdout_candidates.jsonl", "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(len(rows), "questions écrites dans eval/holdout_candidates.jsonl")