"""Simple grammar feedback rules.

This module provides minimal rule-based feedback for learners.  The rules are
intentionally lightweight and focus on common B1-level errors such as misuse of
past simple forms and prepositions.  New rules can be added easily by extending
``RULES``.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import List


@dataclass
class FeedbackRule:
    """Pattern and associated message."""

    pattern: re.Pattern
    message: str


RULES: List[FeedbackRule] = [
    FeedbackRule(
        re.compile(
            r"\bdidn't\s+(?:\w+ed|went|saw|ate|was|were|had|did|made|bought|came)\b",
            re.IGNORECASE,
        ),
        "Use the base form after 'didn't' (e.g., 'didn't go').",
    ),
    FeedbackRule(
        re.compile(
            r"\bin\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b",
            re.IGNORECASE,
        ),
        "Use 'on' with days of the week.",
    ),
    FeedbackRule(
        re.compile(r"\b(he|she|it)\s+(go|do|want|like|eat|need|have)\b", re.IGNORECASE),
        "Add '-s' to the verb in third person singular.",
    ),
    FeedbackRule(
        re.compile(r"\bhave\s+went\b", re.IGNORECASE),
        "Use 'have gone' or 'went' instead of 'have went'.",
    ),
    FeedbackRule(
        re.compile(r"\bat\s+the?\s+morning\b", re.IGNORECASE),
        "Use 'in the morning' instead of 'at the morning'.",
    ),
]


def get_feedback(text: str) -> List[str]:
    """Return feedback messages for the given *text*.

    Parameters
    ----------
    text:
        User provided text to analyse.
    """

    messages: List[str] = []
    for rule in RULES:
        if rule.pattern.search(text):
            messages.append(rule.message)
    return messages
