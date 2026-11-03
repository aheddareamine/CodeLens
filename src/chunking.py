import ast
import json
from pydantic import ValidationError
from corpus import files_to_index, DATA_DIR
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    Language)

from models import Chunk


def py_chunker(file_name: str, max_chunk_size: int):
    chunks = []
    import_blocks = []
    is_module_level_import = True
    imports = ""

    try:
        with open(file_name, "r", encoding="utf-8") as f_py:
            source = f_py.read()
    except (FileNotFoundError, PermissionError, IsADirectoryError) as e:
        print(f"File access error {e}")
        return chunks

    try:
        tree = ast.parse(source)
        lines = source.splitlines(keepends=True)
        line_offsets = [0]
        splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.PYTHON,
            chunk_size=max_chunk_size,
            chunk_overlap=0,
            strip_whitespace=False,
            add_start_index=True)

        for line in lines:
            line_offsets.append(line_offsets[-1] + len(line))

        for block in tree.body:
            block_start = line_offsets[block.lineno - 1] + block.col_offset
            block_end = (
                line_offsets[block.end_lineno - 1] + block.end_col_offset)

            # include decorators for functions and classes
            if isinstance(
                block, (ast.ClassDef,
                        ast.FunctionDef,
                        ast.AsyncFunctionDef))\
                and block.decorator_list:
                
                # whenever a function or class block is found
                # that is the end of the module level imports
                is_module_level_import = False
                first_decorator = block.decorator_list[0]
                block_start = (
                    line_offsets[first_decorator.lineno -1] + block.col_offset)
                block_code = source[block_start:block_end]

            else:
                if not isinstance(block, (ast.Import, ast.ImportFrom)):
                    is_module_level_import = False

            block_code = source[block_start:block_end]

            if len(block_code) <= max_chunk_size:
                chunk = Chunk(
                    file_path=f"{DATA_DIR}/{file_name}",
                    first_character_index=block_start,
                    last_character_index=block_end,
                    text=block_code)

                if isinstance(block, (ast.ImportFrom, ast.Import))\
                    and is_module_level_import:
                        import_blocks.append(chunk)

                else:
                    chunks.append(chunk)

            else:
                documents = splitter.create_documents([block_code])

                for doc in documents:
                    relative_start = doc.metadata["start_index"]

                    absolute_start = block_start + relative_start
                    absolute_end = absolute_start + len(doc.page_content)

                    chunk = Chunk(
                        file_path=f"{DATA_DIR}/{file_name}",
                        first_character_index=absolute_start,
                        last_character_index=absolute_end,
                        text=doc.page_content,
                    )

                    chunks.append(chunk)

        # assemble the chunked module level imports into max_size chunks
        for import_block in import_blocks:
            start = import_block.first_character_index
            end = import_block.last_character_index

            if imports == "":
                imports_start_index = start
                imports_end_index = end
                imports = source[start:end]
                continue

            candidate = source[imports_start_index:end]

            if len(candidate) <= max_chunk_size:
                imports = candidate
                imports_end_index = end
            else:
                chunks.append(Chunk(
                    file_path=f"{DATA_DIR}/{file_name}",
                    first_character_index=imports_start_index,
                    last_character_index=imports_end_index,
                    text=imports,
                ))

                imports_start_index = start
                imports_end_index = end
                imports = source[start:end]

    except (ValidationError, SyntaxError) as e:
        print(f"Chunking error in {file_name}: {e}")


    with open("chunks.json", "w", encoding="utf-8") as output:
        json.dump(
            [chunk.model_dump(mode="json") for chunk in chunks],
            output,
            indent=2,
            ensure_ascii=False,
        )


py_chunker("test.py", 300)