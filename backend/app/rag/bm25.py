"""Okapi BM25 over the indexed document chunks.

The index is built from the chunk texts stored in ChromaDB and kept in
memory (rebuilt when the corpus changes). Pure Python, no dependencies.
"""

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass, field

K1 = 1.5
B = 0.75

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


@dataclass
class BM25Index:
    ids: list[str] = field(default_factory=list)
    term_freqs: list[dict[str, int]] = field(default_factory=list)
    doc_lengths: list[int] = field(default_factory=list)
    document_frequency: dict[str, int] = field(default_factory=dict)
    average_length: float = 0.0

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        """Return ``(chunk_id, score)`` pairs ordered by descending score."""
        query_tokens = tokenize(query)
        if not query_tokens or not self.ids:
            return []

        total_docs = len(self.ids)
        scores: dict[str, float] = {}
        for index, frequencies in enumerate(self.term_freqs):
            score = 0.0
            for token in query_tokens:
                frequency = frequencies.get(token)
                if not frequency:
                    continue
                df = self.document_frequency[token]
                idf = math.log(1.0 + (total_docs - df + 0.5) / (df + 0.5))
                denominator = frequency + K1 * (
                    1.0 - B + B * self.doc_lengths[index] / self.average_length
                )
                score += idf * frequency * (K1 + 1.0) / denominator
            if score > 0.0:
                scores[self.ids[index]] = score

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        return ranked[:top_k]


def build_index(ids: Sequence[str], texts: Sequence[str]) -> BM25Index:
    """Build a BM25 index from chunk ids and their texts."""
    index = BM25Index()
    if not ids:
        return index

    index.ids = list(ids)
    index.term_freqs = []
    index.doc_lengths = []
    frequencies: dict[str, int] = {}

    for text in texts:
        tokens = tokenize(text)
        counts: dict[str, int] = {}
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1
        for token in counts:
            frequencies[token] = frequencies.get(token, 0) + 1
        index.term_freqs.append(counts)
        index.doc_lengths.append(len(tokens))

    index.document_frequency = frequencies
    total = sum(index.doc_lengths)
    index.average_length = (
        (total / len(index.doc_lengths)) if index.doc_lengths else 0.0
    )
    return index
