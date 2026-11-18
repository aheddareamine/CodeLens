"""Build the index (chunks + BM25) on disk and load it back."""

import json
import pickle
from pathlib import Path

from tqdm import tqdm

from src.bm25 import BM25, tokenize
from src.chunking import chunk_file
from src.corpus import find_corpus_files
from src.models import Chunk


def build_index(raw_dir: str, max_chunk_size: int, index_dir: str) -> int:
    """Chunk the corpus, build BM25 and save both in index_dir.

    Returns:
        The number of chunks saved (0 if there was nothing to index).
    """
    files = find_corpus_files(raw_dir)
    if not files:
        print(f"No files to index in {raw_dir}")
        return 0

    chunks: list[Chunk] = []
    for path in tqdm(files, desc="Chunking files"):
        chunks.extend(chunk_file(path.as_posix(), max_chunk_size))

    # chunk i of the list is document i of BM25
    documents: list[list[str]] = []
    for chunk in tqdm(chunks, desc="Tokenizing chunks"):
        # the file path is searched too: questions often name the module
        # ("triton_flash_attention module"). It is only searched, the
        # chunk text and position stay exactly as in the file.
        documents.append(tokenize(chunk.file_path + "\n" + chunk.text))

    bm25 = BM25()
    bm25.build(documents)

    folder = Path(index_dir)
    folder.mkdir(parents=True, exist_ok=True)

    with open(folder / "chunks.json", "w", encoding="utf-8") as file:
        json.dump([chunk.model_dump() for chunk in chunks], file,
                  indent=2, ensure_ascii=False)

    with open(folder / "bm25.pkl", "wb") as file:
        pickle.dump(bm25, file)

    return len(chunks)


def load_index(index_dir: str) -> tuple[list[Chunk], BM25] | None:
    """Load the chunks and the BM25 index saved by build_index.

    Returns:
        (chunks, bm25), or None if the index is missing or broken.
    """
    folder = Path(index_dir)

    try:
        with open(folder / "chunks.json", "r", encoding="utf-8") as file:
            chunks = [Chunk.model_validate(item) for item in json.load(file)]

        with open(folder / "bm25.pkl", "rb") as file:
            bm25: BM25 = pickle.load(file)

    except FileNotFoundError:
        print(f"No index found in {index_dir}, run the index command first")
        return None
    except (OSError, ValueError, pickle.UnpicklingError) as error:
        # ValueError also covers broken JSON and pydantic ValidationError
        print(f"Cannot load the index from {index_dir}: {error}")
        return None

    return chunks, bm25
