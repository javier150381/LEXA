"""Utilities for collecting and processing user feedback."""

from __future__ import annotations

import json
import difflib
from datetime import datetime
from pathlib import Path
from typing import Optional

# Directory where feedback files are stored
FEEDBACK_DIR = Path(__file__).resolve().parent.parent / "data" / "feedback"


def save_feedback(
    generated: str,
    corrected: str,
    feedback_dir: Path | str = FEEDBACK_DIR,
) -> Optional[str]:
    """Store diff between *generated* and *corrected* texts.

    Parameters
    ----------
    generated: str
        Original text produced by the model.
    corrected: str
        Text after user edits.
    feedback_dir: Path or str, optional
        Directory where the feedback files will be stored.

    Returns
    -------
    Optional[str]
        Path to the created feedback file or ``None`` if nothing was stored.
    """

    if not generated or not corrected or generated == corrected:
        return None

    feedback_dir = Path(feedback_dir)
    feedback_dir.mkdir(parents=True, exist_ok=True)

    diff_lines = difflib.unified_diff(
        generated.splitlines(),
        corrected.splitlines(),
        fromfile="generated",
        tofile="corrected",
        lineterm="",
    )
    diff_text = "\n".join(diff_lines)

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    payload = {
        "generated": generated,
        "corrected": corrected,
        "diff": diff_text,
    }
    path = feedback_dir / f"feedback_{timestamp}.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    return str(path)


def process_feedback(
    feedback_dir: Path | str = FEEDBACK_DIR,
    output_file: str = "processed_feedback.jsonl",
) -> Optional[str]:
    """Aggregate feedback pairs for template updates or model training.

    Reads all JSON files from ``feedback_dir`` and produces a JSON Lines file
    with ``{"input": generated, "output": corrected}`` entries.

    Parameters
    ----------
    feedback_dir: Path or str, optional
        Directory containing stored feedback files.
    output_file: str, optional
        Name of the JSONL file to write.

    Returns
    -------
    Optional[str]
        Path to the generated JSONL file or ``None`` if no feedback files were found.
    """

    feedback_dir = Path(feedback_dir)
    if not feedback_dir.exists():
        return None

    entries = []
    for file in sorted(feedback_dir.glob("feedback_*.json")):
        try:
            with file.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            generated = data.get("generated")
            corrected = data.get("corrected")
            if generated and corrected:
                entries.append({"input": generated, "output": corrected})
        except Exception:
            continue

    if not entries:
        return None

    out_path = feedback_dir / output_file
    with out_path.open("w", encoding="utf-8") as out:
        for item in entries:
            json.dump(item, out, ensure_ascii=False)
            out.write("\n")
    return str(out_path)


if __name__ == "__main__":  # pragma: no cover - manual invocation
    process_feedback()
