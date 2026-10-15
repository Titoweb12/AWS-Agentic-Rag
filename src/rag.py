import json
import pathlib
import sys
import faiss
import anthropic
import boto3
import numpy as np
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

DATA = pathlib.Path("data")
TOP_K = 5
MIN_SCORE = 0.15

bedrock = boto3.client("bedrock-runtime")
claude = anthropic.Anthropic()

chunks = [json.loads(l) for l in open(DATA / "chunks.jsonl", encoding="utf-8")]
vectors = np.load(DATA / "embeddings.npy")
index = faiss.IndexFlatIP(vectors.shape[1])
index.add(vectors)


def embed(text):
    body = json.dumps({"inputText": text, "dimensions": 1024, "normalize": True})
    resp = bedrock.invoke_model(modelId="amazon.titan-embed-text-v2:0", body=body)
    return np.array(json.loads(resp["body"].read())["embedding"], dtype="float32")


def retrieve(question, service=None):
    q = embed(question).reshape(1, -1)
    k = len(chunks) if service else TOP_K
    scores, ids = index.search(q, k)
    out = []
    for s, i in zip(scores[0], ids[0]):
        c = chunks[i]
        if service and c["service"] != service:
            continue
        out.append((c, float(s)))
        if len(out) == TOP_K:
            break
    return out

def rewrite(question):
    msg = claude.messages.create(
        model="claude-haiku-5-5",
        max_tokens=500,
        messages=[{
            "role": "user",
                                    "content": (
                "Traduis et reformule cette question en une requête de recherche "
                "en anglais, claire et autonome, pour une base de FAQ AWS. "
                "Le contexte est toujours AWS : « S3 » veut dire Amazon S3. "
                "Réponds uniquement par la requête.\n\n"
                f"Question : {question}"
            ),
        }],
    )
    return "".join(b.text for b in msg.content if b.type == "text").strip()

def answer(question):
    search_query = rewrite(question)
    if search_query == "INCOMPREHENSIBLE":
        return "Je n'ai pas compris la question, peux-tu la reformuler ?", []
    print(f"(recherche : {search_query})")
    results = retrieve(search_query)
    if results[0][1] < MIN_SCORE:
        return "Cette question ne semble pas couverte par la documentation indexée.", results
    context = "\n\n".join(
        f"[{c['id']}]\n{c['text']}" for c, _ in results
    )
    prompt = (
        "Réponds à la question en t'appuyant uniquement sur les extraits de "
        "documentation AWS ci-dessous. Si la réponse n'y figure pas, dis-le. "
        "Cite les identifiants des extraits utilisés entre crochets."
        "Réponds dans la langue utilisée dans la question."
        "Langue de la réponse : celle de la QUESTION ci-dessous (pas celle des extraits).\n\n"
        f"EXTRAITS :\n{context}\n\nQUESTION : {question}"
    )
    msg = claude.messages.create(
        model="claude-haiku-5-5",
        max_tokens=2000,
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
        #print(f"  {c['id']}  score {s:.2f}  {c['question'][:70]}")
        print(f"  {c['id']}  score {s:.2f}  {c['question'][:70]}  {c['url']}")