"""Tokenizer and BM25 ranking, written by hand."""

import math
import re


# Words that appear in almost every question or chunk: they say nothing
# about WHERE the answer is, so we drop them (from chunks and questions).
STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "of", "in", "on", "at", "to", "for", "from", "by", "with", "about",
    "and", "or", "as", "it", "its", "this", "that", "these", "those",
    "what", "which", "who", "how", "when", "where", "why",
    "do", "does", "can", "should", "there", "vllm",
}


# A whole identifier: max_model_len, FusedMoEActivationFormat, fp8, 4096
IDENTIFIER_PATTERN = re.compile(r"[A-Za-z_][A-Za-z_0-9]*|[0-9]+")

# The words inside an identifier (splits "_" and camelCase):
# FusedMoEActivationFormat -> Fused, Mo, E, Activation, Format
WORD_PATTERN = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+")


def tokenize(text: str) -> list[str]:
    """Turn text into lowercase search words: identifiers and their parts.

    "activation_formats" gives "activation_formats", "activation", "formats"
    so a question can match it written in code or in plain English.
    """
    tokens: list[str] = []

    for identifier in IDENTIFIER_PATTERN.findall(text):
        words = [identifier]

        # add the parts only if the identifier really has several,
        # otherwise a plain word like "lora" would be counted twice
        parts = WORD_PATTERN.findall(identifier)
        if len(parts) > 1:
            words.extend(parts)

        for word in words:
            token = word.lower()
            # 1 letter words ("e", "x", "i") are noise
            if len(token) > 1 and token not in STOPWORDS:
                tokens.append(token)

    return tokens


class BM25:
    """BM25 index over a list of tokenized chunks (documents)."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        """Create an empty index. k1: tf saturation, b: length penalty."""
        self.k1 = k1
        self.b = b
        # word -> {document id: how many times the word is in it}
        self.inverted_index: dict[str, dict[int, int]] = {}
        # word -> idf (high for rare words, low for common ones)
        self.idf: dict[str, float] = {}
        self.doc_lengths: list[int] = []
        self.avg_length = 0.0

    def build(self, documents: list[list[str]]) -> None:
        """Count the words of every document and compute their idf."""
        for doc_id in range(len(documents)):
            tokens = documents[doc_id]
            self.doc_lengths.append(len(tokens))

            for token in tokens:
                if token not in self.inverted_index:
                    self.inverted_index[token] = {}

                counts = self.inverted_index[token]
                if doc_id not in counts:
                    counts[doc_id] = 0
                counts[doc_id] += 1

        # 2. average document length, used to penalize long documents
        n = len(documents)
        if n > 0:
            self.avg_length = sum(self.doc_lengths) / n

        # 3. idf of each word: rare words get a high weight
        for token in self.inverted_index:
            df = len(self.inverted_index[token])  # documents with the word
            self.idf[token] = math.log(1 + (n - df + 0.5) / (df + 0.5))

    def word_score(self, tf: int, doc_id: int, idf: float) -> float:
        """BM25 score of one query word in one document."""
        length_ratio = self.doc_lengths[doc_id] / self.avg_length
        length_penalty = self.k1 * (1 - self.b + self.b * length_ratio)
        return idf * tf * (self.k1 + 1) / (tf + length_penalty)

    def search(self, query: str, k: int) -> list[tuple[int, float]]:
        """Score the documents against the query.

        Returns:
            The k best (document id, score), best first.
        """
        scores: dict[int, float] = {}

        # a word repeated in the question only counts once
        query_tokens = set(tokenize(query))

        for token in query_tokens:
            if token not in self.inverted_index:
                continue

            # only the documents that contain this word are visited
            counts = self.inverted_index[token]
            for doc_id in counts:
                score = self.word_score(counts[doc_id], doc_id,
                                        self.idf[token])
                if doc_id not in scores:
                    scores[doc_id] = 0.0
                scores[doc_id] += score

        # sort by score, best first (tuples are sorted by their 1st item)
        ranking: list[tuple[float, int]] = []
        for doc_id in scores:
            ranking.append((scores[doc_id], doc_id))
        ranking.sort(reverse=True)

        best: list[tuple[int, float]] = []
        for score, doc_id in ranking[:k]:
            best.append((doc_id, score))
        return best
