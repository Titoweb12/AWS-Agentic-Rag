import json
import pathlib
import sys

import anthropic
import boto3
import numpy as np
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

DATA = pathlib.Path("data")
TOP_K = 5

bedrock = boto3.client("bedrock-runtime")
claude = anthropic.Anthropic()

chunks = [json.loads(l) for l in open(DATA / "chunks.jsonl", encoding="utf-8")]
vectors = np.load(DATA / "embeddings.npy")


def embed(text):
    body = json.dumps({"inputText": text, "dimensions": 1024, "normalize": True})
    resp = bedrock.invoke_model(modelId="amazon.titan-embed-text-v2:0", body=body)
    return np.array(json.loads(resp["body"].read())["embedding"], dtype="float32")


def retrieve(question):
    scores = vectors @ embed(question)
    best = np.argsort(scores)[::-1][:TOP_K]
    return [(chunks[i], float(scores[i])) for i in best]


def answer(question):
    results = retrieve(question)
    context = "\n\n".join(
        f"[{c['id']}]\n{c['text']}" for c, _ in results
    )
    prompt = (
        "Réponds à la question en t'appuyant uniquement sur les extraits de "
        "documentation AWS ci-dessous. Si la réponse n'y figure pas, dis-le. "
        "Cite les identifiants des extraits utilisés entre crochets.\n\n"
        f"EXTRAITS :\n{context}\n\nQUESTION : {question}"
    )
    msg = claude.messages.create(
        model="claude-haiku-5-5",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in msg.content if b.type == "text")
    return text, results


while True:
    q = input("\nQuestion (vide pour quitter) : ").strip()
    if not q:
        break
    text, results = answer(q)
    print("\n" + text)
    print("\nChunks retrouvés :")
    for c, s in results:
        print(f"  {c['id']}  score {s:.2f}  {c['question'][:70]}")