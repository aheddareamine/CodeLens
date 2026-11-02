from pathlib import Path


class PathValidationError(Exception):
    """Raised when a provided path is invalid"""


class Cli:
    def validate_path(self, path: str, file_type: str = "file"):
        path = Path(path).expanduser()

        if not path.exists():
            raise PathValidationError("Path doesn't exist")

        if file_type == "file" and not path.is_file():
            raise PathValidationError("expected a file but got a directory")

        if file_type == "dir" and not path.is_dir():
            raise PathValidationError("expected a directory but got a file")

        return path


    def index(self, path: str, max_chunk_size=2000):
        "Ingest data/raw/ and build the index under data/processed/."

        path = self.validate_path(path, file_type="dir")

        if max_chunk_size > 2000 or max_chunk_size <= 0:
            raise ValueError(f"{max_chunk_size} is invalid value for max_chunk_size")
        


    def search(self, query: str, k: int):
        "Return the top-k sources for a single query."

        if k <= 0:
            raise ValueError(f"{k} is invalid value for k")


    def search_dataset(self, dataset_path: str, k: int, save_directory: str):
        """Run search over a whole dataset 
        and write a StudentSearchResults JSON file"""

        save_directory = self.validate_path(save_directory, file_type="dir")
        save_directory.mkdir(parents=True, exist_ok=True)
        
        dataset_path = self.validate_path(dataset_path)



    def answer(self, query: str, k: int):
        "Answer a single query using the retrieved context"

        if k <= 0:
            raise ValueError(f"{k} is invalid value for k")


    def answer_dataset(
        self, student_search_results_path: str, save_directory: str):
        """Generate answers for a dataset,
        producing a StudentSearchResultsAndAnswer JSON file."""

        student_search_results_path \
            = self.validate_path(student_search_results_path)
        
        save_directory = self.validate_path(save_directory, file_type="dir")
        save_directory.mkdir(parents=True, exist_ok=True)


        
    def evaluate(self, student_search_results_path: str, dataset_path: str):
        """Report your own recall@k against a ground-truth dataset,
        for your own testing."""
        student_search_results_path = Path(student_search_results_path)
        dataset_path = Path(dataset_path)

        if not student_search_results_path.exists():
            print(f"{student_search_results_path} doesn't exist")

        if not dataset_path.exists():
            print(f"{dataset_path} doesn't exist")
