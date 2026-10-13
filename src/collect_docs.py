import pathlib
import requests
from bs4 import BeautifulSoup

import re
SERVICES = {
    "s3": "https://aws.amazon.com/s3/faqs/",
    "ec2": "https://aws.amazon.com/ec2/faqs/",
    "vpc": "https://aws.amazon.com/vpc/faqs/",
    "iam": "https://aws.amazon.com/iam/faqs/",
    "rds": "https://aws.amazon.com/rds/faqs/",
    "lambda": "https://aws.amazon.com/lambda/faqs/",
    "dynamodb": "https://aws.amazon.com/dynamodb/faqs/",
    "cloudfront": "https://aws.amazon.com/cloudfront/faqs/",
    "sqs": "https://aws.amazon.com/sqs/faqs/",
    "elb": "https://aws.amazon.com/elasticloadbalancing/faqs/",
}

OUT = pathlib.Path("docs/raw")
OUT.mkdir(parents=True, exist_ok=True)

for name, url in SERVICES.items():
    resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
        BLOCKS = ["h1", "h2", "h3", "h4", "h5", "p", "li", "div", "td", "th", "dt", "dd"]
    lines = []
    for el in soup.find_all(BLOCKS):
        if el.find(BLOCKS):  # on ne garde que les blocs "feuilles"
            continue
        t = el.get_text(" ", strip=True)
        t = re.sub(r"\s+([.,;:!?)])", r"\1", t)
        if t:
            lines.append(t)
    text = "\n".join(lines)
    (OUT / f"{name}.txt").write_text(text, encoding="utf-8")
    print(f"{name}: {len(text)} caractères")