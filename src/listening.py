import os
from typing import Tuple

try:  # pragma: no cover - optional dependency
    from openai import OpenAI
except Exception:  # pragma: no cover - provide graceful fallback
    OpenAI = None


def escuchar(audio_path: str | None) -> Tuple[str, str]:
    """Transcribe ``audio_path`` and answer the spoken question.

    Returns a pair (transcription, response). If the OpenAI dependency is not
    available or ``audio_path`` is invalid, an informative message is returned.
    """
    if OpenAI is None:
        return "", "Función no disponible: falta la dependencia 'openai'"

    if not audio_path or not os.path.exists(audio_path):
        return "", "No se proporcionó un audio válido"

    client = OpenAI()
    try:  # pragma: no cover - network call
        with open(audio_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe", file=f
            )
        question = getattr(transcript, "text", "").strip()
        if not question:
            return "", "No se pudo transcribir el audio"

        resp = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {
                    "role": "system",
                    "content": "Eres un asistente que responde en español de forma concisa.",
                },
                {"role": "user", "content": question},
            ],
        )
        answer = resp.output[0].content[0].text  # type: ignore[index]
        return question, answer
    except Exception as exc:  # pragma: no cover - feedback al usuario
        return "", f"Error al procesar el audio: {exc}"
