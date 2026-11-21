"""Answer a question with Qwen3-0.6B from the retrieved sources."""

from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from src.corpus import read_file
from src.models import MinimalSource


MODEL_NAME = "Qwen/Qwen3-0.6B"

# how many tokens of sources we give to the model: more context means
# more chances to have the answer, but a slower and noisier answer on CPU
MAX_CONTEXT_TOKENS = 2500

# the longest answer the model may write
MAX_ANSWER_TOKENS = 200

SYSTEM_PROMPT = (
    "You answer questions about the vLLM project. "
    "Use ONLY the sources given by the user. "
    "If the sources do not contain the answer, say that you could not "
    "find it in the sources. "
    "Answer in a few sentences, and quote exact names from the sources."
)


def source_text(source: MinimalSource) -> str:
    """Read the text a source points to (empty if the file is unreadable)."""
    text = read_file(Path(source.file_path))
    if text is None:
        return ""
    return text[source.first_character_index:source.last_character_index]


class Generator:
    """Qwen3-0.6B, loaded once and used for every question."""

    def __init__(self) -> None:
        """Load the tokenizer and the model (downloaded the first time)."""
        self.tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        # float32: the campus machines have no GPU, and CPUs are
        # fastest and most precise with float32
        # Any: transformers' type hints for generate() confuse mypy
        self.model: Any = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME, dtype=torch.float32)
        self.model.eval()

    def count_tokens(self, text: str) -> int:
        """Number of tokens the model sees for this text."""
        return len(self.tokenizer.encode(text))

    def build_context(self, sources: list[MinimalSource]) -> str:
        """Put the sources together, best first, within the token budget."""
        parts: list[str] = []
        used_tokens = 0

        for number, source in enumerate(sources, start=1):
            text = source_text(source)
            if text == "":
                continue

            part = f"[Source {number}] {source.file_path}\n{text}\n"
            tokens = self.count_tokens(part)

            # the sources are sorted best first: stop at the first one
            # that does not fit, the next ones are less relevant anyway
            if used_tokens + tokens > MAX_CONTEXT_TOKENS:
                break

            parts.append(part)
            used_tokens += tokens

        return "\n".join(parts)

    def answer(self, question: str, sources: list[MinimalSource]) -> str:
        """Generate an answer to the question grounded in the sources."""
        context = self.build_context(sources)
        if context == "":
            return "I could not find any source about this question."

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",
             "content": f"Sources:\n{context}\nQuestion: {question}"},
        ]

        # the chat template adds the special tokens Qwen was trained with.
        # enable_thinking=False: no long <think> reasoning before the answer
        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
            enable_thinking=False)
        inputs = self.tokenizer(prompt, return_tensors="pt")

        # no_grad: we only predict, no training, so no gradients to keep
        with torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=MAX_ANSWER_TOKENS,
                # greedy: always the most likely token, so the same
                # question always gets the same answer
                do_sample=False,
            )

        # generate returns prompt + answer: keep only the new tokens
        prompt_length = inputs["input_ids"].shape[1]
        answer_tokens = output[0][prompt_length:]
        answer = self.tokenizer.decode(answer_tokens, skip_special_tokens=True)
        return str(answer).strip()
