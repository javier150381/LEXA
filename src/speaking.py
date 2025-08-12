"""Feedback wrapper for speaking exercises."""

from __future__ import annotations

from typing import List

from .feedback import get_feedback


def evaluate(transcript: str) -> List[str]:
    """Return feedback messages for a spoken *transcript*.

    This thin wrapper allows other parts of the application to reuse the
    grammar rules defined in :mod:`src.feedback` for speaking tasks.
    """

    return get_feedback(transcript)
