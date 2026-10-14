import json
import boto3
from dotenv import load_dotenv

load_dotenv()
client = boto3.client("bedrock-runtime")

response = client.invoke_model(
    modelId="amazon.titan-embed-text-v2:0",
    body=json.dumps({"inputText": "What is Amazon S3?"}),
)
embedding = json.loads(response["body"].read())["embedding"]
print(len(embedding), embedding[:3])