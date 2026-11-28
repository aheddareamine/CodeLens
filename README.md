*This project has been created as part of the 42 curriculum by aheddar.*

# CodeLens

## Description

CodeLens is a Retrieval-Augmented Generation (RAG) system that answers
questions about the vLLM codebase (version 0.10.1).

It splits the repository into chunks, indexes them with a hand-written BM25,
finds the chunks that best match a question, and gives them to the small
local model `Qwen/Qwen3-0.6B`, which writes an answer based only on those
sources. Retrieval quality is measured with recall@k.

## Instructions

Requirements: Python 3.12+ and [uv](https://docs.astral.sh/uv/).
The model (about 1.5 GB) is downloaded from Hugging Face the first time
an answer command runs.

```bash
make install        # uv sync
make lint           # flake8 + mypy
make clean          # remove caches
```

Put the vLLM repository in `data/raw/` and unzip the datasets in `data/`:

```bash
cd data && unzip datasets_public.zip && cd ..
```

Expected layout:

```
data/raw/vllm-0.10.1/                    corpus to index
data/processed/                          index (chunks.json, bm25.pkl)
data/datasets_public/public/{Unanswered,Answered}Questions/
data/output/search_results/<Scope>/
data/output/search_results_and_answer/<Scope>/
```

Every path is a CLI argument. They all have defaults that follow this
layout, so you only need to pass them when you use other locations.

## Example usage

```bash
# 1. build the index (default chunk size: 2000 characters)
uv run python -m src index --max_chunk_size 2000

# 2. search one question
uv run python -m src search "How do I load a LoRA adapter?" --k 5

# 3. search a whole dataset
uv run python -m src search_dataset \
    --dataset_path data/datasets_public/public/UnansweredQuestions/dataset_code_public.json \
    --k 10 \
    --save_directory data/output/search_results/UnansweredQuestions

# 4. check our own recall@k (the official score comes from the moulinette)
uv run python -m src evaluate \
    --student_search_results_path data/output/search_results/UnansweredQuestions/dataset_code_public.json \
    --dataset_path data/datasets_public/public/AnsweredQuestions/dataset_code_public.json

# 5. answer one question, or a whole search result file
uv run python -m src answer "How do I load a LoRA adapter?" --k 5
uv run python -m src answer_dataset \
    --student_search_results_path data/output/search_results/UnansweredQuestions/dataset_docs_public.json \
    --save_directory data/output/search_results_and_answer/UnansweredQuestions
```

Shortcuts thanks to the defaults:

- `search_dataset` without `--save_directory` writes to
  `data/output/search_results/<scope of the dataset>/`.
- `evaluate` without `--dataset_path` uses the file with the same name in
  `data/datasets_public/public/AnsweredQuestions/`.
- `answer_dataset` without `--save_directory` writes to
  `data/output/search_results_and_answer/<scope of the results>/`.
- `--index_dir` (default `data/processed`) and `--raw_dir` (default
  `data/raw`) select another index or corpus.

## System architecture

```
data/raw ──> corpus.py ──> chunking.py ──> bm25.py ──> data/processed
             (pick files)  (cut chunks)    (index)     chunks.json + bm25.pkl
                                                              │
question ──> search.py (BM25 top-k) ──> sources ──> generator.py (Qwen3) ──> answer
                                           │
                                     evaluate.py (recall@k)
```

| File | Role |
|------|------|
| `models.py` | pydantic models from the subject, plus `Chunk` (a source with its text) |
| `corpus.py` | lists the files to index, reads a file as text |
| `chunking.py` | Python chunker and Markdown/text chunker |
| `bm25.py` | tokenizer and BM25 index, written by hand |
| `indexer.py` | builds the index and saves it, loads it back |
| `search.py` | top-k search for one question or a whole dataset, JSON I/O |
| `generator.py` | builds the prompt and generates the answer with Qwen3-0.6B |
| `evaluate.py` | recall@k with the same IoU rule as the moulinette |
| `cli.py` | the Fire commands, argument checks and error messages |

Document `i` of BM25 is chunk `i` of `chunks.json`, so a BM25 result
directly gives back a file path and a character range.

## Chunking strategy

Indexed files: every `.md` and `.txt` file, and the `.py` files of the
`vllm/` package. This matches where the answers live: docs questions point
to `.md` / `.txt` files, code questions to `vllm/*.py`. Tests, examples and
benchmarks are left out because they add noise.

**Python files** are parsed with `ast`. Each top-level statement (import,
function, class, assignment) becomes a chunk that keeps its decorators.
Consecutive module-level imports are grouped together until they reach
the size limit. A block bigger than `max_chunk_size` is cut between lines,
so no line is split unless a single line is longer than the limit.
A file that `ast` cannot parse (syntax error, null bytes) is not dropped:
it is cut between lines instead, so it stays searchable.

**Markdown files** are cut at headings (`#` lines outside ``` code blocks),
so each chunk is about one topic. Small sections are merged until the size
limit, and a section that is too big is cut between lines. `.txt` files have
no headings and are only cut between lines.

Character positions are exact: files are read with `newline=""` so `\r\n` is
not changed, and no chunk is longer than 2000 characters (the moulinette
rejects longer sources).

## Retrieval method

**Tokenizer.** Questions often use plain words while code uses identifiers,
so each identifier is kept whole and also split into its parts:
`max_model_len` gives `max_model_len`, `max`, `model`, `len`, and
`FusedMoE` gives `fusedmoe`, `fused`, `mo`. Everything is lowercased, and
1-letter tokens and stopwords (`the`, `what`, `how`, `vllm`...) are dropped.

**Indexed text.** Each chunk is indexed with its file path in front of it,
because questions often name the module ("the triton_flash_attention
module"). Only the searched text changes: the stored range stays exact.

**BM25** (k1 = 1.5, b = 0.75) uses an inverted index (word to
{chunk id: count}), so a query only visits the chunks that contain one of
its words. For each query word:

```
idf   = log(1 + (N - df + 0.5) / (df + 0.5))
score = idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * length / avg_length))
```

Rare words weigh more (idf), repeating a word helps less and less (k1), and
long chunks are penalized (b). The k best chunks are returned.

## Answer generation

The retrieved chunks are read back from the corpus and put in the prompt,
best first, until a budget of 2500 tokens is reached. The system prompt asks
the model to use only these sources and to say when the answer is not in
them. Qwen's chat template is used with thinking turned off, and decoding is
greedy, so the same question always gets the same answer (at most 200
tokens). The model is loaded once per command, not once per question.

## Performance analysis

Measured on the public datasets with the moulinette, `--k 10`
(16 cores, no GPU):

| Chunk size | Docs R@1 | Docs R@3 | Docs R@5 | Docs R@10 | Code R@1 | Code R@3 | Code R@5 | Code R@10 |
|-----------:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|
| **2000** | 0.67 | 0.80 | **0.85** | 0.90 | 0.49 | 0.72 | **0.79** | 0.88 |
| 1000 | 0.70 | 0.83 | 0.86 | 0.90 | 0.56 | 0.71 | 0.79 | 0.87 |
| 500 | 0.66 | 0.79 | 0.85 | 0.89 | 0.43 | 0.70 | 0.77 | 0.85 |

Targets: 80% recall@5 on docs and 50% on code, so both pass. Smaller
chunks change little: the IoU bar is low (0.05), so a big chunk that covers
the right region already counts, and very small chunks lose context words.

| Step | Time | Limit |
|------|-----:|------:|
| `index` (1083 files, 16684 chunks) | 11 s | 5 min |
| `search_dataset` (100 questions, model loading included) | 3 s | 90 s for 200 |
| `answer` (one question, model loading included) | about 35 s | none |
| `answer_dataset` | about 25 s per question | none |

## Design decisions

- **BM25 instead of TF-IDF**: it handles chunks of different lengths and
  stops a word repeated 50 times from dominating the score.
- **Hand-written BM25** with plain dicts: easy to explain, fast enough
  (a few ms per query), and no extra dependency.
- **Two chunkers**: code is cut on syntax (functions, classes) and docs on
  headings, because that is where each kind of file changes topic.
- **Index saved on disk** (JSON for the chunks, pickle for BM25): searching
  never rebuilds anything.
- **Errors are printed, never raised**: every command checks its arguments
  and files, and prints a message instead of a traceback.
- **CPU-only PyTorch** in `pyproject.toml`: the campus machines have no GPU,
  and the default build pulls several GB of CUDA libraries.

## Challenges faced

- **Exact character ranges.** `ast` gives column offsets in bytes, not
  characters, which broke ranges on files with non-ASCII text. Chunks now
  end at line boundaries computed from the text itself.
- **Questions vs identifiers.** Plain-word questions did not match
  `snake_case` / `CamelCase` names. Splitting identifiers into their parts
  and indexing the file path helped the code questions most.
- **Headings in code blocks.** `# comment` lines inside ``` blocks were taken
  for Markdown headings. The chunker now tracks whether it is inside a code
  block.
- **A small model.** Qwen3-0.6B can ignore the sources or ramble. A strict
  system prompt, a limited context with the best sources first and thinking
  mode turned off keep its answers short and grounded.

## Resources

- Robertson and Zaragoza, *The Probabilistic Relevance Framework: BM25 and
  Beyond* (2009)
- Python `ast` module documentation
- Hugging Face Transformers documentation and the Qwen3-0.6B model card
- Python Fire, pydantic and uv documentation

### How AI was used

An AI assistant (Claude) was used as a tutor: to explain concepts (BM25,
IoU, chat templates), to review code and point out bugs and edge cases, to
run the timing and edge-case tests, and to help write this README.