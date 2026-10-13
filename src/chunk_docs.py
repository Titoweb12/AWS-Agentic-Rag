import json
import pathlib
import re

RAW = pathlib.Path("docs/raw")
OUT = pathlib.Path("data")
OUT.mkdir(exist_ok=True)

MAX_CHARS = 1200
MIN_ANSWER = 40  # ignore les titres de section et le bruit


def is_question(line):
    return line.endswith("?") and len(line) < 250


def parse_qa(text):
    """Retourne une liste de (question, réponse). Ignore les questions sans réponse."""
    pairs, question, answer = [], None, []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if is_question(line):
            if question and answer:
                pairs.append((question, " ".join(answer)))
            question, answer = line, []
        elif question and len(line) >= MIN_ANSWER:
            answer.append(line)
    if question and answer:
        pairs.append((question, " ".join(answer)))
    return pairs


def split_answer(question, answer):
    if len(question) + len(answer) <= MAX_CHARS:
        return [answer]
    sentences = re.split(r"(?<=[.!?])\s+", answer)
    parts, current = [], ""
    for s in sentences:
        if current and len(question) + len(current) + len(s) > MAX_CHARS:
            parts.append(current)
            current = ""
        current = f"{current} {s}".strip()
    if current:
        parts.append(current)
    return parts


total = 0
with open(OUT / "chunks.jsonl", "w", encoding="utf-8") as f:
    for path in sorted(RAW.glob("*.txt")):
        service = path.stem
        count = 0
        for question, answer in parse_qa(path.read_text(encoding="utf-8")):
            for part in split_answer(question, answer):
                record = {
                    "id": f"{service}-{count}",
                    "service": service,
                    "question": question,
                    "text": f"{question}\n{part}",
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                count += 1
        print(f"{service}: {count} chunks")
        total += count

print(f"Total : {total} chunks")