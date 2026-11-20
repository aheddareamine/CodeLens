from pathlib import Path


def is_wanted(relative_path: Path) -> bool:
    """Tell whether a file is indexed."""
    extension = relative_path.suffix

    if extension in (".md", ".txt"):
        return True

    if extension == ".py":
        parts = relative_path.parts
        return len(parts) > 2 and parts[1] == "vllm"

    return False


def find_corpus_files(raw_dir: str) -> list[Path]:
    """List the files to index, sorted."""
    root = Path(raw_dir)
    if not root.is_dir():
        print(f"Error: {raw_dir} is not a directory")
        return []

    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if is_wanted(path.relative_to(root)):
            files.append(path)
    # sort to make sure the indexes are the same between runs
    files.sort()
    return files


def read_file(path: Path) -> str | None:
    """Read a whole file as text, or return None if it cannot be read."""
    try:
        # newline="" keeps "\r\n" as is, otherwise Python turns it into
        # "\n" and every character index after it would be shifted.
        with open(path, "r", encoding="utf-8", newline="") as file:
            return file.read()
    except (OSError, UnicodeDecodeError) as error:
        print(f"Warning: could not read {path}: {error}")
        return None
