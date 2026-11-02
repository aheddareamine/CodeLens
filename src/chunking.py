import ast
from pydantic import ValidationError
from corpus import files_to_index, DATA_DIR
from models import Chunk


def py_chunker(file_name: str, max_chunk_size: int):
    chunks = []
    import_blocks = []
    is_module_level_import = True

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
        
        for line in lines:
            line_offsets.append(line_offsets[-1] + len(line))

        for block in tree.body:
            # include decorators for functions and classes
            if isinstance(
                block, (ast.ClassDef,
                        ast.FunctionDef,
                        ast.AsyncFunctionDef)) and block.decorator_list:
                
                first_decorator = block.decorator_list[0]
                start = (line_offsets[first_decorator.lineno - 1] + block.col_offset)
                end = line_offsets[block.end_lineno - 1] + block.end_col_offset
                block_code = source[start:end]

            else:
                block_code = ast.get_source_segment(source, block)

            if len(block_code) > max_chunk_size:
                if isinstance(block, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    pass

                elif isinstance(block, ast.ClassDef):
                    pass

                elif isinstance(block, (ast.ImportFrom, ast.Import)):
                    if import_blocks:
                        curr_index = block.col_offset + line_offsets[block.lineno - 1]
                        prev_index = import_blocks[-1]["end_index"]

                        if source[prev_index:curr_index].isspace():
                            chunk = Chunk(
                                file_path=f"{DATA_DIR}/{file_name}",
                                first_character_index=(block.col_offset + line_offsets[block.lineno - 1]),
                                last_character_index=block.end_col_offset + line_offsets[block.end_lineno - 1],
                                text=block_code)

                            import_blocks.append(chunk)

                    else:
                        


            




            
            
            
            

    

    #         if len(block_code) > max_chunk_size:
    #             if isinstance(block, ast.ClassDef):
    #                 # chunk_class_code(block, chunks)
    #                 pass
    #             elif isinstance(block, ast.FunctionDef):
    #                 # chunk_function_code(block, chunks)
    #                 pass
    #             else:
    #                 # chunk_by_lines(block, chunks)
    #                 pass

    #         else:
    #             if isinstance(block, (ast.Import, ast.ImportFrom)):
    #                 import_blocks.append(
    #                     {"code": block_code,
    #                     "start_index": (block.col_offset),
    #                     "end_index": (block.end_col_offset)}
    #                     )

    #             else:
    #                 chunk = Chunk(
    #                     file_path=f"{DATA_DIR}/{file_name}",
    #                     first_character_index=block.col_offset,
    #                     last_character_index=block.end_col_offset,
    #                     text=ast.get_source_segment(source, block))

    #                 chunks.append(chunk)

    #     imports = ""
    #     for import_block in import_blocks:
    #         if imports == "":
    #             imports_start_index = import_block["start_index"]

    #         if len(imports) + len(import_block["code"]) <= max_chunk_size:
    #                 imports += "\n" + import_block["code"]
    #                 imports_end_index = import_block["end_index"]

    #         else:
    #             chunk = Chunk(
    #                     file_path=f"{DATA_DIR}/{file_name}",
    #                     first_character_index=imports_start_index,
    #                     last_character_index=imports_end_index,
    #                     text=imports)
    #             chunks.append(chunk)

    #             imports_start_index = import_block["start_index"]
    #             imports = import_block["code"]
    #             imports_end_index = import_block["end_index"]

    #     if imports != "":
    #         chunk = Chunk(
    #                 file_path=f"{DATA_DIR}/{file_name}",
    #                 first_character_index=imports_start_index,
    #                 last_character_index=imports_end_index,
    #                 text=imports)
    #         chunks.append(chunk)

    except (ValidationError):
        print("invalid chunking data")


    with open("chunks", "w", encoding="utf-8") as output:
        for chunk in chunks:
            output.write(chunk.model_dump_json(indent=2))


py_chunker("test.py", 300)