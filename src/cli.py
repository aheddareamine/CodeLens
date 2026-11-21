from pathlib import Path

from tqdm import tqdm

from src.evaluate import recall_at_k
from src.generator import Generator
from src.indexer import build_index, load_index
from src.models import MinimalAnswer, StudentSearchResultsAndAnswer
from src.search import (load_dataset, load_search_results, save_json,
                        search_dataset, search_sources)


def load_generator() -> Generator | None:
    """Load Qwen3-0.6B.

    Returns:
        The generator, or None (after printing why) if it cannot load.
    """
    print("Loading the model...")
    try:
        return Generator()
    except (OSError, ValueError) as error:
        # OSError: no internet and the model is not in the cache yet
        print(f"Error: cannot load the model: {error}")
        return None


def validate_path(path: str, file_type: str = "file") -> Path | None:
    """Check that path exists and is a file (or a directory).

    Returns:
        The path as a Path object, or None (after printing why) if invalid.
    """
    checked_path = Path(str(path)).expanduser()

    if not checked_path.exists():
        print(f"Error: {path} doesn't exist")
        return None

    if file_type == "file" and not checked_path.is_file():
        print(f"Error: {path}: expected a file, got a directory")
        return None

    if file_type == "dir" and not checked_path.is_dir():
        print(f"Error: {path}: expected a directory, got a file")
        return None

    return checked_path


def is_valid_k(k: int) -> bool:
    """Tell whether k is a positive integer (prints an error if not)."""
    # Fire gives a str for "--k abc" and a bool for "--k" alone
    if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
        print(f"Error: k must be a positive integer, got {k!r}")
        return False
    return True


def make_save_folder(save_directory: str) -> Path | None:
    """Create the output folder if needed.

    Returns:
        The folder, or None if it cannot be created.
    """
    folder = Path(str(save_directory)).expanduser()
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        print(f"Error: cannot create {save_directory}: {error}")
        return None
    return folder


class Cli:
    """The commands of the subject. Fire exposes every public method."""

    def index(self, max_chunk_size: int = 2000, raw_dir: str = "data/raw",
              index_dir: str = "data/processed") -> None:
        """Ingest data/raw/ and build the index under data/processed/."""
        # Fire gives a str if the user types --max_chunk_size abc
        if isinstance(max_chunk_size, bool) or \
                not isinstance(max_chunk_size, int) or \
                not 0 < max_chunk_size <= 2000:
            print("Error: max_chunk_size must be an integer between 1 "
                  "and 2000")
            return

        try:
            count = build_index(raw_dir, max_chunk_size, index_dir)
        except OSError as error:
            print(f"Error while indexing: {error}")
            return

        if count > 0:
            print(f"Ingestion complete! {count} chunks, indices saved "
                  f"under {index_dir}/")

    def search(self, query: str, k: int = 10,
               index_dir: str = "data/processed") -> None:
        """Return the top-k sources for a single query."""
        # Fire turns "search 42" into the int 42
        query = str(query)
        if query.strip() == "":
            print("Error: the query is empty")
            return
        if not is_valid_k(k):
            return

        index = load_index(index_dir)
        if index is None:
            return
        chunks, bm25 = index

        sources = search_sources(chunks, bm25, query, k)
        if not sources:
            print("No results: no word of the query is in the index")
            return

        for rank, source in enumerate(sources, start=1):
            print(f"{rank}. {source.file_path} "
                  f"[{source.first_character_index}:"
                  f"{source.last_character_index}]")

    def search_dataset(self, dataset_path: str, k: int,
                       save_directory: str,
                       index_dir: str = "data/processed") -> None:
        """Run search over a whole dataset
        and write a StudentSearchResults JSON file"""
        if not is_valid_k(k):
            return

        dataset_file = validate_path(dataset_path)
        if dataset_file is None:
            return

        dataset = load_dataset(dataset_file)
        if dataset is None:
            return

        # load the index once, not once per question
        index = load_index(index_dir)
        if index is None:
            return
        chunks, bm25 = index

        folder = make_save_folder(save_directory)
        if folder is None:
            return

        print(f"Loaded {len(dataset.rag_questions)} questions")
        results = search_dataset(dataset, chunks, bm25, k)

        # same file name as the dataset: the folder tells which scope it is
        output_file = folder / dataset_file.name
        if save_json(results, output_file):
            print(f"Saved student_search_results to {output_file}")

    def answer(self, query: str, k: int = 10,
               index_dir: str = "data/processed") -> None:
        """Answer a single query using the retrieved context"""
        query = str(query)
        if query.strip() == "":
            print("Error: the query is empty")
            return
        if not is_valid_k(k):
            return

        index = load_index(index_dir)
        if index is None:
            return
        chunks, bm25 = index
        sources = search_sources(chunks, bm25, query, k)

        generator = load_generator()
        if generator is None:
            return

        print(generator.answer(query, sources))
        print("\nSources:")
        for source in sources:
            print(f"  {source.file_path} "
                  f"[{source.first_character_index}:"
                  f"{source.last_character_index}]")

    def answer_dataset(self, student_search_results_path: str,
                       save_directory: str) -> None:
        """Generate answers for a dataset,
        producing a StudentSearchResultsAndAnswer JSON file."""
        results_file = validate_path(student_search_results_path)
        if results_file is None:
            return
        results = load_search_results(results_file)
        if results is None:
            return
        folder = make_save_folder(save_directory)
        if folder is None:
            return

        # load the model once, not once per question
        generator = load_generator()
        if generator is None:
            return

        print(f"Loaded {len(results.search_results)} questions")
        answers: list[MinimalAnswer] = []
        for result in tqdm(results.search_results, desc="Answering"):
            answers.append(MinimalAnswer(
                question_id=result.question_id,
                question=result.question,
                retrieved_sources=result.retrieved_sources,
                answer=generator.answer(result.question,
                                        result.retrieved_sources),
            ))
        print(f"Processed {len(answers)} of {len(results.search_results)} "
              f"questions")

        output = StudentSearchResultsAndAnswer(search_results=answers,
                                               k=results.k)
        output_file = folder / results_file.name
        if save_json(output, output_file):
            print(f"Saved student_search_results_and_answer to "
                  f"{output_file}")

    def evaluate(self, student_search_results_path: str,
                 dataset_path: str) -> None:
        """Report your own recall@k against a ground-truth dataset,
        for your own testing."""
        results_file = validate_path(student_search_results_path)
        dataset_file = validate_path(dataset_path)
        if results_file is None or dataset_file is None:
            return

        results = load_search_results(results_file)
        dataset = load_dataset(dataset_file)
        if results is None or dataset is None:
            return

        # same k values as the moulinette, up to the k we searched with
        for k in (1, 3, 5, 10):
            if k > results.k:
                break
            recall, _missed = recall_at_k(results, dataset, k)
            print(f"Recall@{k}: {recall:.3f}")

        # the misses at @5 (the pass/fail k) are what we have to improve
        _recall, missed = recall_at_k(results, dataset, min(5, results.k))
        print(f"\n{len(missed)} questions with no source found "
              f"in the top {min(5, results.k)}:")
        for question in missed:
            print(f"  - {question}")
