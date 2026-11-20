from pathlib import Path

from src.indexer import build_index


class PathValidationError(Exception):
    """Raised when a provided path is invalid"""


def validate_path(path: str, file_type: str = "file") -> Path:
    """Check that path exists and is a file (or a directory).

    Returns:
        The path as a Path object.
    """
    checked_path = Path(path).expanduser()

    if not checked_path.exists():
        raise PathValidationError(f"{path} doesn't exist")

    if file_type == "file" and not checked_path.is_file():
        raise PathValidationError(f"{path}: expected a file, got a directory")

    if file_type == "dir" and not checked_path.is_dir():
        raise PathValidationError(f"{path}: expected a directory, got a file")

    return checked_path


class Cli:
    """The commands of the subject. Fire exposes every public method."""

    def index(self, max_chunk_size: int = 2000, raw_dir: str = "data/raw",
              index_dir: str = "data/processed") -> None:
        """Ingest data/raw/ and build the index under data/processed/."""
        # Fire gives a str if the user types --max_chunk_size abc
        if not isinstance(max_chunk_size, int) or \
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

    def search(self, query: str, k: int) -> None:
        """Return the top-k sources for a single query."""
        if k <= 0:
            raise ValueError(f"{k} is invalid value for k")

    def search_dataset(self, dataset_path: str, k: int,
                       save_directory: str) -> None:
        """Run search over a whole dataset
        and write a StudentSearchResults JSON file"""
        dataset_file = validate_path(dataset_path)

        # an output folder may not exist yet: create it, don't validate it
        save_folder = Path(save_directory)
        save_folder.mkdir(parents=True, exist_ok=True)

    def answer(self, query: str, k: int) -> None:
        """Answer a single query using the retrieved context"""
        if k <= 0:
            raise ValueError(f"{k} is invalid value for k")

    def answer_dataset(self, student_search_results_path: str,
                       save_directory: str) -> None:
        """Generate answers for a dataset,
        producing a StudentSearchResultsAndAnswer JSON file."""
        search_results_file = validate_path(student_search_results_path)

        save_folder = Path(save_directory)
        save_folder.mkdir(parents=True, exist_ok=True)

    def evaluate(self, student_search_results_path: str,
                 dataset_path: str) -> None:
        """Report your own recall@k against a ground-truth dataset,
        for your own testing."""
        search_results_file = validate_path(student_search_results_path)
        dataset_file = validate_path(dataset_path)
