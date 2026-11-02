from pathlib import Path

DATA_DIR = Path("../data/raw/vllm-0.10.1/vllm")

files_to_index = []
count = 0

for file in DATA_DIR.rglob("*"):
    if file.suffix in {".py", ".md"}:
        files_to_index.append(file.relative_to(DATA_DIR))