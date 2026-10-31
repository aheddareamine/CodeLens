from pathlib import Path

DATA_DIR = Path("../data/raw/vllm-0.10.1/vllm")

count = 0
for file in DATA_DIR.rglob("*"):
    if file.suffix == {".py", ".md"}:
        print(file.relative_to(DATA_DIR))

print(count)