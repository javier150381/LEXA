import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lib import voice


def test_conversar_transcribe_and_save(tmp_path, monkeypatch):
    audio_file = tmp_path / "sample.wav"
    audio_file.write_bytes(b"data")

    fake_model = MagicMock()
    fake_model.transcribe.return_value = {"text": "hola"}
    fake_whisper = MagicMock()
    fake_whisper.load_model.return_value = fake_model
    monkeypatch.setitem(sys.modules, "whisper", fake_whisper)

    fake_llm = MagicMock()
    fake_llm.invoke.return_value = MagicMock(content="respuesta")
    monkeypatch.setattr(voice, "ChatOpenAI", MagicMock(return_value=fake_llm))

    resp = voice.conversar(str(audio_file), storage_dir=tmp_path)

    assert resp == "respuesta"
    saved = list(tmp_path.glob("sample_*.txt"))
    assert len(saved) == 1
    assert saved[0].read_text() == "hola"
