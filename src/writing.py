"""Feedback wrapper for writing exercises."""

from __future__ import annotations

from typing import List

from .feedback import get_feedback


def evaluate(text: str) -> List[str]:
    """Return feedback messages for a written *text*.

    The function reuses the rule-based system defined in :mod:`src.feedback` to
    provide grammar hints for writing tasks.
    """

    return get_feedback(text)
