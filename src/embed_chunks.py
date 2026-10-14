import json
import time
import pathlib

import boto3
import numpy as np
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()
client = boto3.client("bedrock-runtime")

DATA = pathlib.Path("data")
MODEL_ID = "amazon.titan-embed-text-v2:0"


def embed(text, retries=5):
    body = json.dumps({"inputText": text, "dimensions": 1024, "normalize": True})
    for attempt in range(retries):
        try:
            resp = client.invoke_model(modelId=MODEL_ID, body=body)
            return json.loads(resp["body"].read())["embedding"]
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == "ThrottlingException" and attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise


chunks = [json.loads(l) for l in open(DATA / "chunks.jsonl", encoding="utf-8")]
vectors = []
for i, chunk in enumerate(chunks):
    vectors.append(embed(chunk["text"]))
    if (i + 1) % 100 == 0:
        print(f"{i + 1}/{len(chunks)}")

np.save(DATA / "embeddings.npy", np.array(vectors, dtype="float32"))
print("Terminé :", len(vectors), "vecteurs")