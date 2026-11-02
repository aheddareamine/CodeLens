"""AST chunking fixture: module documentation with Unicode café and λ.

Use this module to test exact source spans, semantic boundaries, and size limits.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, TypeVar

# This comment is not represented as a standalone AST statement.
CONSTANT = "A string with an emoji 🐍 and a newline\\ninside"
MULTILINE = (
    "first segment "
    "second segment "
    "third segment"
)

"A standalone string expression that is NOT the module docstring."

T = TypeVar("T")


def trace(label: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator factory with a nested function and a closure."""
    def decorate(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            print(f"TRACE {label}: {func.__name__}")
            return func(*args, **kwargs)
        return wrapper
    return decorate


@dataclass(slots=True)
class Record:
    """A small model with a class docstring, fields, and a method."""
    key: str
    values: list[int] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(self.values)

    def normalized(self) -> dict[str, float]:
        """Return a dictionary with a Unicode local variable."""
        μέσος = self.total / len(self.values) if self.values else 0
        return {"average": μέσος, "count": float(len(self.values))}


class Store:
    """Class containing methods, nested loops, and exception handling."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.records: dict[str, Record] = {}

    @trace("load")
    def load(self, filename: str) -> Record:
        path = self.root / filename
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ValueError(f"Missing file: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed JSON: {path}") from exc
        record = Record(key=str(payload["key"]), values=list(payload["values"]))
        self.records[record.key] = record
        return record

    def group(self) -> dict[str, list[int]]:
        groups: dict[str, list[int]] = defaultdict(list)
        for record in self.records.values():
            for number in record.values:
                if number < 0:
                    continue
                if number % 2 == 0:
                    groups["even"].append(number)
                else:
                    groups["odd"].append(number)
        return dict(groups)


@trace("transform")
def transform(items: Iterable[str], *, upper: bool = False) -> list[str]:
    """A decorated function with a multiline signature and a comprehension."""
    return [item.strip().upper() if upper else item.strip() for item in items]


async def fetch_simulated(name: str) -> dict[str, str]:
    """An async function containing await and an async context switch."""
    await asyncio.sleep(0)
    return {"name": name, "status": "ready"}


def generator(limit: int):
    """A generator with yield, for, and if statements."""
    for number in range(limit):
        if number % 3 == 0:
            yield number


def nested_scope(value: int) -> int:
    """A nested function is not a top-level tree.body entry."""
    def double(number: int) -> int:
        return number * 2
    return double(value)


# An intentionally long top-level function for max_chunk_size splitting tests.
def oversized_function(items: list[int]) -> dict[str, Any]:
    """This function is intentionally longer than 2,000 characters.

    A chunker must not emit the whole function as one chunk when the size cap
    is 2,000. Split at safe internal statement boundaries or use another
    documented fallback that preserves correct character offsets.
    """
    result: dict[str, Any] = {"count": len(items), "steps": []}
    for item in items:
        if item < 0:
            result["steps"].append(("negative", item))
        elif item == 0:
            result["steps"].append(("zero", item))
        else:
            result["steps"].append(("positive", item))
    # The following repeated narrative comments are deliberate: comments
    # occupy source positions but are not separately exposed by ast.parse.
    # Fixture padding 1: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 2: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 3: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 4: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 5: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 6: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 7: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 8: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 9: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 10: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 11: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 12: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 13: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 14: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 15: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 16: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 17: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 18: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 19: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 20: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 21: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 22: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 23: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 24: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 25: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 26: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 27: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 28: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 29: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 30: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 31: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 32: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 33: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 34: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    # Fixture padding 35: source offsets and context windows must remain accurate after splitting; preserve nearby comments.
    for index, value in enumerate(items):
        match value:
            case 0:
                result["steps"].append(("match-zero", index))
            case x if x > 10:
                result["steps"].append(("match-large", x))
            case _:
                result["steps"].append(("match-other", value))
    return result


if __name__ == "__main__":
    example = Record("demo", [1, 2, 3])
    print(example.normalized())
