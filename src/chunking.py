import ast
from pathlib import Path
from pydantic import ValidationError

from src.corpus import read_file
from src.models import Chunk


def split_by_lines(text: str, max_chunk_size: int) -> list[tuple[int, str]]:
    """Cut text between lines into pieces of at most max_chunk_size chars.

    Returns:
        A list of (start index of the piece inside text, piece text).
    """
    pieces = []
    current = ""
    current_start = 0
    position = 0

    for line in text.splitlines(keepends=True):
        # the line doesn't fit: save the current piece and start a new one
        if current and len(current) + len(line) > max_chunk_size:
            pieces.append((current_start, current))
            current = ""
            current_start = position

        # the line alone is too long: cut it in hard pieces
        while len(line) > max_chunk_size:
            pieces.append((position, line[:max_chunk_size]))
            line = line[max_chunk_size:]
            position += max_chunk_size
            current_start = position

        current += line
        position += len(line)

    if current:
        pieces.append((current_start, current))
    return pieces


def py_chunker(file_name: str, max_chunk_size: int) -> list[Chunk]:
    """Chunk a Python file by top-level blocks (imports, classes, functions).

    Returns:
        The chunks of the file (empty list if it cannot be read).
    """
    chunks: list[Chunk] = []
    import_blocks: list[Chunk] = []
    is_module_level_import = True
    imports = ""

    # read_file also catches UnicodeDecodeError (a file that is not utf-8)
    source = read_file(Path(file_name))
    if source is None:
        return chunks

    try:
        tree = ast.parse(source)
        lines = source.splitlines(keepends=True)
        line_offsets = [0]

        for line in lines:
            line_offsets.append(line_offsets[-1] + len(line))

        for block in tree.body:
            # end_lineno is typed "int | None" by mypy
            end_lineno = block.end_lineno or block.lineno

            block_start = line_offsets[block.lineno - 1] + block.col_offset
            # end at the start of the next line (= end of the block's last
            # line). Not end_col_offset: ast counts it in bytes, not chars.
            block_end = line_offsets[end_lineno]

            # include decorators for functions and classes
            if (isinstance(block, (ast.ClassDef,
                                   ast.FunctionDef,
                                   ast.AsyncFunctionDef))
                    and block.decorator_list):
                # whenever a function or class block is found
                # that is the end of the module level imports
                is_module_level_import = False
                first_decorator = block.decorator_list[0]
                decorator_line = first_decorator.lineno - 1
                block_start = line_offsets[decorator_line] + block.col_offset

            else:
                if not isinstance(block, (ast.Import, ast.ImportFrom)):
                    is_module_level_import = False

            block_code = source[block_start:block_end]

            if len(block_code) <= max_chunk_size:
                chunk = Chunk(
                    file_path=file_name,
                    first_character_index=block_start,
                    last_character_index=block_end,
                    text=block_code)

                is_import = isinstance(block, (ast.ImportFrom, ast.Import))

                if is_import and is_module_level_import:
                    import_blocks.append(chunk)

                else:
                    chunks.append(chunk)

            else:
                pieces = split_by_lines(block_code, max_chunk_size)

                for relative_start, piece in pieces:
                    absolute_start = block_start + relative_start
                    absolute_end = absolute_start + len(piece)

                    chunk = Chunk(
                        file_path=file_name,
                        first_character_index=absolute_start,
                        last_character_index=absolute_end,
                        text=piece,
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
                    file_path=file_name,
                    first_character_index=imports_start_index,
                    last_character_index=imports_end_index,
                    text=imports,
                ))

                imports_start_index = start
                imports_end_index = end
                imports = source[start:end]

        # don't forget the last group of imports
        if imports != "":
            chunks.append(Chunk(
                file_path=file_name,
                first_character_index=imports_start_index,
                last_character_index=imports_end_index,
                text=imports,
            ))

    except (ValidationError, SyntaxError) as e:
        print(f"Chunking error in {file_name}: {e}")

    return chunks


def md_chunker(file_name: str, max_chunk_size: int) -> list[Chunk]:
    """Chunk a Markdown file by sections (headings), a .txt file by lines.

    Returns:
        The chunks of the file (empty list if it cannot be read).
    """
    chunks: list[Chunk] = []

    source = read_file(Path(file_name))
    if source is None:
        return chunks

    section_starts = [0]

    if file_name.endswith(".md"):
        in_code_block = False
        position = 0

        for line in source.splitlines(keepends=True):
            # inside ``` blocks, "# ..." is a shell comment, not a heading
            if line.lstrip().startswith("```"):
                in_code_block = not in_code_block
            elif line.startswith("#") and not in_code_block and position > 0:
                section_starts.append(position)
            position += len(line)

    section_starts.append(len(source))

    current_start = 0
    current_end = 0

    for i in range(len(section_starts) - 1):
        start = section_starts[i]
        end = section_starts[i + 1]

        if end - start > max_chunk_size:
            # save what we have, then split this big section
            if current_end > current_start:
                chunks.append(Chunk(
                    file_path=file_name,
                    first_character_index=current_start,
                    last_character_index=current_end,
                    text=source[current_start:current_end],
                ))

            pieces = split_by_lines(source[start:end], max_chunk_size)

            for relative_start, piece in pieces:
                absolute_start = start + relative_start
                chunks.append(Chunk(
                    file_path=file_name,
                    first_character_index=absolute_start,
                    last_character_index=absolute_start + len(piece),
                    text=piece,
                ))

            current_start = end
            current_end = end

        elif end - current_start <= max_chunk_size:
            # the section still fits in the current chunk
            current_end = end

        else:
            # it doesn't fit: save the current chunk, start a new one
            chunks.append(Chunk(
                file_path=file_name,
                first_character_index=current_start,
                last_character_index=current_end,
                text=source[current_start:current_end],
            ))
            current_start = start
            current_end = end

    # don't forget the last chunk
    if current_end > current_start:
        chunks.append(Chunk(
            file_path=file_name,
            first_character_index=current_start,
            last_character_index=current_end,
            text=source[current_start:current_end],
        ))

    return chunks


def chunk_file(file_name: str, max_chunk_size: int) -> list[Chunk]:
    """Chunk one file with the strategy that fits its extension."""
    if file_name.endswith(".py"):
        return py_chunker(file_name, max_chunk_size)

    return md_chunker(file_name, max_chunk_size)
