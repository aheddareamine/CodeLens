"""Our own recall@k, computed the same way as the moulinette."""

from src.models import (AnsweredQuestion, MinimalSource, RagDataset,
                        StudentSearchResults)


# a retrieved source counts as found from this overlap (subject: IoU 0.05)
MIN_IOU = 0.05


def iou(a: MinimalSource, b: MinimalSource) -> float:
    """Intersection over union of two character ranges (0 if other file)."""
    if a.file_path != b.file_path:
        return 0.0

    intersection = (min(a.last_character_index, b.last_character_index)
                    - max(a.first_character_index, b.first_character_index))
    if intersection <= 0:
        return 0.0

    union = (max(a.last_character_index, b.last_character_index)
             - min(a.first_character_index, b.first_character_index))
    return intersection / union


def is_found(expected: MinimalSource, retrieved: list[MinimalSource]) -> bool:
    """Tell whether one of the retrieved sources overlaps the expected one."""
    for source in retrieved:
        if iou(expected, source) >= MIN_IOU:
            return True
    return False


def recall_at_k(results: StudentSearchResults, dataset: RagDataset,
                k: int) -> tuple[float, list[str]]:
    """Average, over the questions, of the share of sources found in top-k.

    Returns:
        (recall, the questions with no source found).
    """
    # question_id -> the retrieved sources, best first
    retrieved_by_id: dict[str, list[MinimalSource]] = {}
    for result in results.search_results:
        retrieved_by_id[result.question_id] = result.retrieved_sources

    total = 0.0
    count = 0
    missed: list[str] = []

    for question in dataset.rag_questions:
        # only answered questions have ground-truth sources
        if not isinstance(question, AnsweredQuestion):
            continue
        if not question.sources:
            continue

        # a question we have no result for counts as 0
        retrieved = retrieved_by_id.get(question.question_id, [])
        top_k = retrieved[:k]

        found = 0
        for expected in question.sources:
            if is_found(expected, top_k):
                found += 1

        total += found / len(question.sources)
        count += 1
        if found == 0:
            missed.append(question.question)

    if count == 0:
        return 0.0, missed
    return total / count, missed
