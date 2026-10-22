# AWS Agentic RAG

A question-answering system over the official FAQ pages of 10 AWS services, built twice: a naive RAG pipeline and a LangGraph agent. The two are compared on a hand-checked evaluation set, with a control for the effect of prompting.

**Main finding:** most of the agent's measured advantage comes from a stricter generation prompt, not from the graph. A naive RAG given the same prompt reaches 96% faithfulness (the agent: 98%). The agent keeps a small edge on a few hard cases, at the cost of at least twice as many model calls.

## What it does

Ask a question about S3, EC2, VPC, IAM, RDS, Lambda, DynamoDB, CloudFront, SQS or ELB, in English, French, Italian or German. The system retrieves passages from the FAQs, answers only from them, cites the passage IDs and the source URL, and says so when the documentation does not cover the question.

## Architecture

```
FAQ pages -> text -> chunks (one per Q&A) -> Titan embeddings -> FAISS index
```

- **Corpus:** the FAQ page of each of the 10 services, 2,004 chunks. One chunk per question and answer; long answers are split on sentence boundaries. Each chunk carries its service, question and source URL.
- **Embeddings:** Amazon Titan Text Embeddings V2 on Bedrock (1024 dimensions, normalized). Search is an exact inner-product index with FAISS.
- **Models:** Claude Haiku 5.5 for routing, query rewriting, relevance grading, generation and judging.

### Naive RAG (`src/rag.py`)

Rewrite the question as an English search query, retrieve the top 5 passages, generate an answer with citations. `src/rag_strict.py` is the same pipeline with the generation prompt of the agent.

### Agent (`src/agent.py`, LangGraph)

```
route -> rewrite -> retrieve -> grade -> generate
  |         ^                      |
  |         +-- not relevant, <2 --+
  |                                +-- still nothing --> "I don't know"
  +-- off topic --> polite refusal
```

- **Router:** JSON output; sends clearly unrelated questions (and questions about other cloud providers) to a refusal, and detects the question language.
- **Relevance grader:** few-shot prompt; keeps only passages that contain the requested information and says whether they are enough to answer.
- **Rewrite loop:** up to 2 more reformulations when the grader finds nothing.
- **Generator:** answers only from the kept passages, cites them, and states what the excerpts do not cover. The answer is written in the language of the question.

## Evaluation

- 50 English questions (46 answerable, 4 that should be refused) and 12 multilingual questions (fr, it, de). Most answerable questions were generated from corpus passages and reviewed by hand; the rest were written by hand, including questions that need vocabulary the user would not use.
- Every question is asked 3 times per system.
- **hit@5:** the expected passage is among the 5 retrieved. **Used:** it was given to the generator.
- **Faithfulness:** every claim of the answer is explicitly in the passages given. Judged by an LLM from the same model family as the generator.

### Results (46 answerable questions x 3 runs)

| Metric | Naive RAG (original prompt) | Naive RAG (strict prompt) | Agent |
|---|---|---|---|
| hit@5 | 96% | 95% | 97% |
| Expected passage used | 96% | 95% | 95% |
| Answer given | 99% | 99% | 96% |
| Faithfulness | 84% | 96% | 98% |
| Answer in the question's language | 81% | 100% | 100% |
| Correct refusals (12) | 100% | 100% | 100% |
| Model calls per question | 2 | 2 | 4 or more |

Full tables, multilingual results and limitations: [`eval/baseline.md`](eval/baseline.md).

### What the evaluation found

- **The prompt mattered more than the graph.** Tightening the generator (answer only from the excerpts, no guessed causes, say what is not covered) took faithfulness from 84% to 96% in the naive pipeline too.
- **The first agent was worse than the naive RAG.** Before corrections it refused about 15% of answerable questions. The causes: a router that rejected vague but valid questions, and a relevance grader that saw passages truncated to 700 characters (23% of chunks are longer). Fixing both brought "answer given" from 85% to 96%.
- **Some of the early numbers were measurement errors.** The agent's answers ended with a "Sources" line that the faithfulness judge counted as unsupported claims; the agent's first faithfulness score was 46%, and 77% once that was fixed. One test question also expected a single passage while two were valid.
- **Where the agent still helps:** a question about triggering a Lambda function from an S3 upload (the naive pipeline misses it in most runs, because the question does not use the AWS term "event notifications"), and one Italian question.

### Known limits

- The corrections were chosen by looking at failures of this same question set, so the final numbers are optimistic. A set of unseen questions is still to do.
- Few questions need several steps, so the rewrite loop is rarely used (0.12 rewrites per question).
- 46 questions repeated 3 times are not 138 independent questions.
- The faithfulness judge is a model of the same family as the generator and sometimes flags trivial sentences.
- A persistent failure: "How do I enable S3 event notifications?" is refused by the agent in 3 of 3 runs.
- FAQ pages answer "what is X" well and integration scenarios between services poorly.
- The refusal message of the naive pipeline is written in French only, whatever the question language.

## Run it

Requires Python 3.12, an Anthropic API key, and an AWS account with Bedrock access to Titan Text Embeddings V2 (an IAM user restricted to `bedrock:InvokeModel` on that model is enough).

```
python -m venv .venv
source .venv/Scripts/activate        # Windows Git Bash; use .venv/bin/activate on Linux and macOS
pip install -r requirements.txt
```

Create a `.env` file (it is git-ignored):

```
ANTHROPIC_API_KEY=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=eu-central-1
```

Build the index, then ask questions:

```
python src/collect_docs.py      # download the FAQ pages into docs/raw
python src/chunk_docs.py        # build data/chunks.jsonl
python src/embed_chunks.py      # embed the chunks with Titan (about a cent)
python src/rag.py               # naive RAG
python src/agent.py             # LangGraph agent
streamlit run src/app.py        # web interface (agent or naive RAG)

```
### With Docker

The image contains the code only. The data folder is mounted at run time and the API keys come from your `.env` file.

```
docker build --load -t aws-agentic-rag .
docker run --rm -p 8501:8501 --env-file .env -v "$(pwd)/data:/app/data:ro" aws-agentic-rag
```

Then open http://localhost:8501. On Windows Git Bash, prefix the second command with `MSYS_NO_PATHCONV=1` and use `$(pwd -W)` instead of `$(pwd)`.

Run the evaluation:

```
python eval/run_eval.py --runs 3
python eval/run_eval.py --runs 3 --systems naif_strict
python eval/analyze.py          # classify the failures of the last run
```

On Windows, set `PYTHONUTF8=1` (or run `python -X utf8 ...`) so accents print correctly.

The FAQ texts belong to AWS and are not stored in this repository: `docs/raw/` and `data/` are git-ignored and rebuilt by the scripts above.

## Repository layout

```
Dockerfile  image that runs the Streamlit app
src/        collect_docs, chunk_docs, embed_chunks, rag, rag_strict, agent, app
eval/       questions.jsonl, multilingual.jsonl, run_eval.py, analyze.py, baseline.md
```

## Decisions worth knowing

- ChromaDB was the first choice for the vector store. Its native code crashed on Windows in two versions, so the index uses FAISS.
- Embeddings use Titan on Bedrock instead of a local model: no local PyTorch install, and the project stays on AWS.
- The naive pipeline was kept untouched as a reference while the agent was corrected, so that each correction could be measured against it.
