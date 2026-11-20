"""Search the index: one question, or a whole dataset of questions."""

import json
from pathlib import Path

from pydantic import BaseModel
from tqdm import tqdm

from src.bm25 import BM25
from src.models import (Chunk, MinimalSearchResults, MinimalSource,
                        RagDataset, StudentSearchResults)


def search_sources(chunks: list[Chunk], bm25: BM25, query: str,
                   k: int) -> list[MinimalSource]:
    """Find the k chunks that best match the query.

    Returns:
        Their locations (file, start, end), best first.
    """
    sources: list[MinimalSource] = []

    # BM25 gives document ids: document i is chunk i of chunks.json
    for doc_id, _score in bm25.search(query, k):
        chunk = chunks[doc_id]
        sources.append(MinimalSource(
            file_path=chunk.file_path,
            first_character_index=chunk.first_character_index,
            last_character_index=chunk.last_character_index,
        ))

    return sources


def search_dataset(dataset: RagDataset, chunks: list[Chunk], bm25: BM25,
                   k: int) -> StudentSearchResults:
    """Search every question of the dataset.

    Returns:
        The results in the format the moulinette reads.
    """
    results: list[MinimalSearchResults] = []

    for question in tqdm(dataset.rag_questions, desc="Searching"):
        sources = search_sources(chunks, bm25, question.question, k)
        # keep the question_id: the grader matches results to the
        # ground truth with it
        results.append(MinimalSearchResults(
            question_id=question.question_id,
            question=question.question,
            retrieved_sources=sources,
        ))

    return StudentSearchResults(search_results=results, k=k)


def load_dataset(path: Path) -> RagDataset | None:
    """Read a questions JSON file.

    Returns:
        The dataset, or None if the file is unreadable or malformed.
    """
    try:
        with open(path, "r", encoding="utf-8") as file:
            return RagDataset.model_validate(json.load(file))
    except (OSError, ValueError) as error:
        # ValueError covers broken JSON and pydantic ValidationError
        print(f"Error: cannot read the dataset {path}: {error}")
        return None


def load_search_results(path: Path) -> StudentSearchResults | None:
    """Read a StudentSearchResults JSON file written by search_dataset.

    Returns:
        The results, or None if the file is unreadable or malformed.
    """
    try:
        with open(path, "r", encoding="utf-8") as file:
            return StudentSearchResults.model_validate(json.load(file))
    except (OSError, ValueError) as error:
        print(f"Error: cannot read the search results {path}: {error}")
        return None


def save_json(data: BaseModel, path: Path) -> bool:
    """Write a pydantic model to a JSON file.

    Returns:
        True if the file was written.
    """
    try:
        with open(path, "w", encoding="utf-8") as file:
            file.write(data.model_dump_json(indent=2))
    except OSError as error:
        print(f"Error: cannot write {path}: {error}")
        return False
    return True
