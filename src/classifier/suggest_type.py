"""Simple case type classifier based on keyword matching.

This module provides the :func:`suggest_type` function which receives a
free-form case description and returns a list of probable categories.  The
classifier uses a naïve keyword lookup; it is intended as a lightweight hint
for the user and does **not** replace expert review.
"""
from __future__ import annotations

from collections import Counter
import re
import unicodedata
from typing import Iterable, List

# Mapping of category names to sets of keywords.  The keywords are compared
# case-insensitively on whole words.
CATEGORY_KEYWORDS = {
    "Laboral": {"despido", "salario", "empleador", "trabajo"},
    "Civil": {"contrato", "arrendamiento", "propiedad", "daño"},
    "Familiar": {"divorcio", "pensión", "custodia", "matrimonio"},
    "Penal": {"delito", "robo", "hurto", "acusado"},
    "Mercantil": {"sociedad", "acción", "comercio", "empresa"},
}

_word_re = re.compile(r"\w+")


def _normalize(text: str) -> str:
    """Return ``text`` lowercased and stripped of accents."""
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def _tokenize(text: str) -> Iterable[str]:
    for match in _word_re.finditer(text.lower()):
        yield match.group(0)


def suggest_type(description: str, top_n: int = 3) -> List[str]:
    """Return the most probable categories for ``description``.

    Parameters
    ----------
    description:
        Free-form text describing the case.
    top_n:
        Maximum number of categories to return.
    """
    tokens = list(_tokenize(description))
    if not tokens:
        return []

    counts: Counter[str] = Counter()
    token_set = {_normalize(t) for t in tokens}
    for category, keywords in CATEGORY_KEYWORDS.items():
        normalized_keywords = {_normalize(k) for k in keywords}
        if token_set & normalized_keywords:
            counts[category] = len(token_set & normalized_keywords)

    return [c for c, _ in counts.most_common(top_n)]
