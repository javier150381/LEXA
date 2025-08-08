import json
from pathlib import Path

from lib.feedback import save_feedback, process_feedback


def test_save_and_process_feedback(tmp_path):
    generated = "Hola"
    corrected = "Hola Mundo"
    file_path = save_feedback(generated, corrected, tmp_path)
    assert file_path is not None
    path = Path(file_path)
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["generated"] == generated
    assert data["corrected"] == corrected
    out = process_feedback(tmp_path)
    assert out is not None
    out_path = Path(out)
    assert out_path.exists()
    line = out_path.read_text(encoding="utf-8").strip()
    assert json.loads(line) == {"input": generated, "output": corrected}
