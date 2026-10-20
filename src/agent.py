import json
import pathlib
import re
import sys
from typing import TypedDict

import anthropic
import boto3
import faiss
import numpy as np
from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

DATA = pathlib.Path("data")
TOP_K = 5
MAX_REFORMULATIONS = 2
MODEL = "claude-haiku-5-5"

bedrock = boto3.client("bedrock-runtime")
claude = anthropic.Anthropic()

chunks = [json.loads(l) for l in open(DATA / "chunks.jsonl", encoding="utf-8")]
vectors = np.load(DATA / "embeddings.npy")
assert len(chunks) == len(vectors)
index = faiss.IndexFlatIP(vectors.shape[1])
index.add(vectors)


# ---------- outils ----------
def ask(prompt, max_tokens=800):
    msg = claude.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if b.type == "text").strip()


def ask_json(prompt):
    raw = ask(prompt)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    try:
        return json.loads(match.group(0))
    except (AttributeError, json.JSONDecodeError):
        return {}


def embed(text):
    body = json.dumps({"inputText": text, "dimensions": 1024, "normalize": True})
    resp = bedrock.invoke_model(modelId="amazon.titan-embed-text-v2:0", body=body)
    return np.array(json.loads(resp["body"].read())["embedding"], dtype="float32")


def retrieve(query):
    if not query.strip():
        return []
    q = embed(query).reshape(1, -1)
    scores, ids = index.search(q, TOP_K)
    return [(chunks[i], float(s)) for s, i in zip(scores[0], ids[0])]


# ---------- état ----------
class State(TypedDict, total=False):
    question: str
    route: str
    search_query: str
    reformulations: int
    passages: list
    relevant: list
    sufficient: bool
    answer: str
    language: str


# ---------- nœuds ----------
def route_node(state):
    out = ask_json(
        "Decide whether this question could be answered with AWS documentation. "
        'Answer "aws" if it is about AWS, or about cloud and IT infrastructure '
        "(hosting a website, storage, databases, networking, IP addresses, "
        "load balancing, permissions, messaging, serverless), even when no AWS "
        "service is named, because the user may be asking about their own AWS "
        'setup. Answer "off_topic" only if the question is clearly unrelated '
        "to cloud and IT infrastructure (sports, cooking, general knowledge), or "
        "is about another provider's product (Azure, Google Cloud). "
        "Also give the language the question is written in (for example English, "
        'French, Italian). Reply with JSON only: {"route": "aws" or "off_topic", '
        '"language": "..."}.\n\n'
        f"Question: {state['question']}"
    )
    route = out.get("route", "aws")  # en cas de doute, on laisse passer
    language = out.get("language", "the same language as the question")
    print(f"[route] {route} ({language})")
    return {"route": route, "language": language}

def rewrite_node(state):
    previous = state.get("search_query")
    if previous is None:
        query = ask(
            "Traduis et reformule cette question en une requête de recherche en "
            "anglais, claire et autonome, pour une base de FAQ AWS. "
            "Réponds uniquement par la requête.\n\n"
            f"Question : {state['question']}",
            1000,
        )
        query = query or state["question"]
        print(f"[rewrite] {query}")
        return {"search_query": query, "reformulations": 0}
    query = ask(
        "Une recherche n'a pas ramené de passages pertinents. Propose une requête "
        "différente en anglais (autre vocabulaire, noms officiels des services et "
        "fonctionnalités AWS). Réponds uniquement par la requête.\n\n"
        f"Question : {state['question']}\nRequête précédente : {previous}",
        1000,
    )
    query = query or previous
    n = state["reformulations"] + 1
    print(f"[rewrite #{n}] {query}")
    return {"search_query": query, "reformulations": n}


def retrieve_node(state):
    passages = retrieve(state["search_query"])
    print("[retrieve] " + ", ".join(f"{c['id']}({s:.2f})" for c, s in passages))
    return {"passages": passages}



GRADE_INSTRUCTIONS = (
    "Tu évalues si des passages de FAQ AWS permettent de répondre à une question. "
    "Retiens uniquement les passages qui contiennent réellement l'information "
    "demandée : un passage qui parle d'un sujet voisin n'est pas pertinent. "
    "'sufficient' vaut true seulement si les passages retenus permettent de "
    "répondre. "
    "Pour une question qui compare deux sujets, 'sufficient' vaut true si chaque "
    "sujet est couvert par un passage, même si aucun passage ne les compare "
    "directement. "
    'Réponds uniquement en JSON : {"relevant_ids": [...], "sufficient": true|false}.\n\n'
)



FEWSHOT = """Exemple 1
Question : How can I trigger a Lambda function when an object is uploaded to S3?
Passages :
[s3-375] What is S3 Object Lambda? S3 Object Lambda runs a Lambda function on GET, LIST and HEAD requests to transform data as it is retrieved.
[lambda-22] How can my application trigger an AWS Lambda function directly? Use the Invoke API with a custom event.
Réponse : {"relevant_ids": [], "sufficient": false}

Exemple 2
Question : What is the difference between a security group and a network ACL?
Passages :
[vpc-53] What are the differences between security groups in a VPC and network ACLs? Security groups are stateful and apply to instances; network ACLs are stateless and apply to subnets.
[elb-135] Can I configure a security group for the front-end of Classic Load Balancers?
Réponse : {"relevant_ids": ["vpc-53"], "sufficient": true}

Exemple 3
Question : What is the maximum size of an S3 object?
Passages :
[s3-5] How much data can I store in Amazon S3? Objects can range from 0 bytes up to the maximum object size.
[s3-216] Is there a minimum billable object size for S3 Intelligent-Tiering?
Réponse : {"relevant_ids": ["s3-5"], "sufficient": true}

Exemple 4
Question : What is the difference between Amazon CloudFront and a network ACL?
Passages :
[cloudfront-0] What is Amazon CloudFront? CloudFront is a web service that distributes content with low latency using a global network of edge locations.
[vpc-53] What are the differences between security groups in a VPC and network ACLs? Network ACLs are stateless and apply to subnets.
Réponse : {"relevant_ids": ["cloudfront-0", "vpc-53"], "sufficient": true}

Maintenant, à toi.
"""


def grade_node(state):
    listing = "\n".join(f"[{c['id']}] {c['text']}" for c, _ in state["passages"])
    out = ask_json(
        GRADE_INSTRUCTIONS
        + FEWSHOT
        + f"Question : {state['question']}\nPassages :\n{listing}\nRéponse :"
    )
    ids = set(out.get("relevant_ids", []))
    relevant = [c for c, _ in state["passages"] if c["id"] in ids]
    sufficient = bool(out.get("sufficient")) and bool(relevant)
    print(f"[grade] pertinents={sorted(ids)} suffisant={sufficient}")
    return {"relevant": relevant, "sufficient": sufficient}


def after_grade(state):
    if state["sufficient"]:
        return "generate"
    if state["reformulations"] < MAX_REFORMULATIONS:
        return "rewrite"
    return "unknown"


def generate_node(state):
    context = "\n\n".join(f"[{c['id']}]\n{c['text']}" for c in state["relevant"])
    text = ask(
        "Answer the question using ONLY the excerpts below.\n"
        "Rules:\n"
        "- State only what the excerpts say. Do not guess causes, do not assume "
        "what the user's situation probably is, and do not add advice that the "
        "excerpts do not give.\n"
        "- If the excerpts describe the general behaviour but not the user's "
        "specific situation, give the general information and say clearly that "
        "the excerpts do not cover that specific situation.\n"
        "- Cite the excerpt identifiers in square brackets after each statement, "
        "for example [s3-184].\n"
        f"- Write the entire answer in {state['language']}, whatever the language "
        "of the excerpts.\n\n"
        f"EXCERPTS:\n{context}\n\nQUESTION: {state['question']}",
        1000,
    )
    urls = sorted({c["url"] for c in state["relevant"]})
    return {"answer": text + "\n\nSources : " + ", ".join(urls)}


def say(state, text):
    out = ask(
        f"Translate this message into {state['language']}. "
        "If it is already in that language, repeat it. Reply with the message only.\n\n"
        + text,
        1000,
    )
    return out or text


def unknown_node(state):
    return {"answer": say(state, "I don't know: I could not find a reliable source "
                                 "in the indexed documentation to answer this question.")}


def refuse_node(state):
    return {"answer": say(state, "This question is not about the covered AWS services "
                                 "(S3, EC2, VPC, IAM, RDS, Lambda, DynamoDB, CloudFront, SQS, ELB).")}
# ---------- graphe ----------
graph = StateGraph(State)
graph.add_node("route", route_node)
graph.add_node("rewrite", rewrite_node)
graph.add_node("retrieve", retrieve_node)
graph.add_node("grade", grade_node)
graph.add_node("generate", generate_node)
graph.add_node("unknown", unknown_node)
graph.add_node("refuse", refuse_node)

graph.add_edge(START, "route")
graph.add_conditional_edges(
    "route",
    lambda s: "aws" if s["route"] == "aws" else "off_topic",
    {"aws": "rewrite", "off_topic": "refuse"},
)
graph.add_edge("rewrite", "retrieve")
graph.add_edge("retrieve", "grade")
graph.add_conditional_edges(
    "grade",
    after_grade,
    {"generate": "generate", "rewrite": "rewrite", "unknown": "unknown"},
)
graph.add_edge("generate", END)
graph.add_edge("unknown", END)
graph.add_edge("refuse", END)

app = graph.compile()

if __name__ == "__main__":
    while True:
        q = input("\nQuestion (vide pour quitter) : ").strip()
        if not q:
            break
        result = app.invoke({"question": q})
        print("\n" + result["answer"])